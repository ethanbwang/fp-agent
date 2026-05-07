from collections import defaultdict
from itertools import pairwise
import os
import statistics
from typing import Any

from dotenv import load_dotenv
import orjson
import numpy as np

from classifier_training.feature_index import BROWSER_FEATURE_INDICES

load_dotenv()

PROJECT_ROOT = os.getenv("PROJECT_ROOT")


class BehavioralFV:
    def __init__(self, feature_vector: list[float] | None = None):
        self.EVENT_TYPES = {"p", "i", "mm", "md", "mu", "kd", "ku", "sc", "se", "c"}

        # Map mouse button/key to list of events
        self.mouse_down_counts = defaultdict[int, list[list[Any]]](list)
        self.mouse_up_counts = defaultdict[int, list[list[Any]]](list)
        self.key_down_counts = defaultdict[str, list[list[Any]]](list)
        self.key_up_counts = defaultdict[str, list[list[Any]]](list)
        self.feature_vector = feature_vector

    def parse_events(self, events: list[list[Any]], max_time_interval: float = 300):
        self.events = self.sort_events(events)
        self.event_counts = self.count_events()
        self.max_time_interval = max_time_interval

    def count_events(self) -> dict[str, list[list[Any]]]:
        """Counts the number of events of each type"""
        counts = {event_type: [] for event_type in self.EVENT_TYPES}
        for event in self.events:
            assert event[0] in self.EVENT_TYPES, f"Invalid event type: {event[0]}"
            counts[event[0]].append(event)
            if event[0] == "md":
                self.mouse_down_counts[event[2]].append(event)
            elif event[0] == "mu":
                self.mouse_up_counts[event[2]].append(event)
            elif event[0] == "kd":
                self.key_down_counts[event[2]].append(event)
            elif event[0] == "ku":
                self.key_up_counts[event[2]].append(event)
        return counts

    def sort_events(self, events: list[list[Any]]) -> list[list[Any]]:
        """Sorts events by timestamp"""
        return sorted(events, key=lambda x: x[-1])

    def read_behavioral_data(self, events: list[list[Any]]):
        for event in events:
            assert event[0] in self.EVENT_TYPES, f"Invalid event type: {event[0]}"
            self.events[event[0]].append(event)

    def group_bursts(
        self, event_types: list[str] | None = None, max_time_interval: float = 300
    ) -> list[list[list[Any]]]:
        """
        Groups events into bursts. Assumes self.events is sorted by timestamp.

        Args:
            max_time_interval (float): Maximum time interval between events in a burst (ms)
        """
        assert all(
            event in self.EVENT_TYPES for event in event_types
        ), f"Invalid event type: {event_types}"
        if not self.events:
            return []

        events = (
            self.events
            if event_types is None
            else [e for e in self.events if e[0] in event_types]
        )
        bursts: list[list[list[Any]]] = []
        current_burst = [events[0]]
        last_event_time = events[0][-1]
        for event in events[1:]:
            if event[-1] - last_event_time < max_time_interval:
                current_burst.append(event)
            else:
                bursts.append(current_burst)
                current_burst = [event]
            last_event_time = event[-1]
        bursts.append(current_burst)
        return bursts

    def _get_ratio(self, numerator: int, denominator: int) -> float:
        if denominator == 0:
            if numerator == 0:
                return -1
            return 0
        return numerator / denominator

    def _get_distance(self, p1: tuple[float, float], p2: tuple[float, float]) -> float:
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

    def _get_stats(self, values: list[float]) -> tuple[float, float, float, float]:
        return (
            statistics.mean(values),
            statistics.median(values),
            max(values) - min(values),
            statistics.stdev(values) if len(values) > 1 else -1,
        )

    def _get_scroll_bursts_by_element(
        self,
    ) -> dict[str, list[list[tuple[str, str, float, float, float]]]]:
        if not self.event_counts["sc"] or not self.event_counts["se"]:
            return {}

        event_list = [e for e in self.events if e[0] in ["sc", "se"]]

        events_by_element: dict[str, list[tuple[str, str, float, float, float]]] = {}
        for event in event_list:
            if events_by_element.get(event[1], None) is None:
                events_by_element[event[1]] = []
            events_by_element[event[1]].append(event)

        element_scroll_bursts: dict[
            str, list[list[tuple[str, str, float, float, float]]]
        ] = {}
        for element_id, events in events_by_element.items():
            element_scroll_bursts[element_id] = []
            cur_burst = []
            for event in events:
                cur_burst.append(event)
                if event[0] == "se":
                    element_scroll_bursts[element_id].append(cur_burst)
                    cur_burst = []

        return element_scroll_bursts

    def get_all_scroll_data(self) -> list[tuple[float, float]]:
        if not self.event_counts["sc"] or not self.event_counts["se"]:
            return []

        element_scroll_bursts = self._get_scroll_bursts_by_element()
        res = []

        for element_bursts in element_scroll_bursts.values():
            prev_scroll_pos = None

            for burst in element_bursts:
                start_time = burst[0][-1]
                end_time = burst[-1][-1]
                if end_time != start_time:
                    # More than one event in burst
                    duration = end_time - start_time

                    distance = sum(
                        self._get_distance((a[2], a[3]), (b[2], b[3]))
                        for a, b in pairwise(burst)
                    )

                    if prev_scroll_pos is not None:
                        distance += self._get_distance(
                            prev_scroll_pos, (burst[0][2], burst[0][3])
                        )

                    res.append((duration, distance))

                # Update the previous scroll position for the element
                prev_scroll_pos = (burst[-1][2], burst[-1][3])

        return res

    def _process_scroll_bursts(self) -> dict[str, tuple[float, float, float, float]]:
        """
        Processes scroll bursts. Returns -1 for all stats if no scroll events.
        sc event: ("sc", element_id, x, y, timestamp)
        """
        if not self.event_counts["sc"]:
            return {
                "distance": (-1, -1, -1, -1),
                "time": (-1, -1, -1, -1),
            }

        element_scroll_bursts = self._get_scroll_bursts_by_element()

        distances = []
        times = []

        for element_bursts in element_scroll_bursts.values():
            prev_scroll_pos = None

            for burst in element_bursts:
                start_time = burst[0][-1]
                end_time = burst[-1][-1]
                if end_time != start_time:
                    # More than one event in burst
                    duration = end_time - start_time

                    distance = sum(
                        self._get_distance((a[2], a[3]), (b[2], b[3]))
                        for a, b in pairwise(burst)
                    )

                    if prev_scroll_pos is not None:
                        distance += self._get_distance(
                            prev_scroll_pos, (burst[0][2], burst[0][3])
                        )

                    distances.append(distance)
                    times.append(duration)
                else:
                    # Only one event in burst
                    if prev_scroll_pos is not None:
                        distances.append(
                            self._get_distance(
                                prev_scroll_pos, (burst[0][2], burst[0][3])
                            )
                        )
                    # No duration, so time is N/A

                # Update the previous scroll position for the element
                prev_scroll_pos = (burst[-1][2], burst[-1][3])

        return {
            "distance": (
                self._get_stats(distances) if len(distances) > 0 else (-1, -1, -1, -1)
            ),
            "time": self._get_stats(times) if len(times) > 0 else (-1, -1, -1, -1),
        }

    def _is_valid_segment(self, segment: list[list[Any]]) -> list[list[Any]] | None:
        """
        Returns deduplicated segment if valid otherwise None.
        """
        deduplicated_segment = []
        prev_coords = None
        for event in segment:
            cur_coords = (
                (event[2], event[3]) if event[0] == "mm" else (event[3], event[4])
            )
            if cur_coords != prev_coords:
                prev_coords = cur_coords
                deduplicated_segment.append(event)
        return deduplicated_segment if len(deduplicated_segment) >= 3 else None

    def _get_direction(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        dx, dy = b[0] - a[0], b[1] - a[1]
        return float(np.degrees(np.arctan2(dy, dx)))

    def _get_angle_of_curvature(
        self, a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
    ) -> float:
        # Vectors BA and BC
        BA = np.array(a) - np.array(b)
        BC = np.array(c) - np.array(b)
        cos_angle = np.dot(BA, BC) / (np.linalg.norm(BA) * np.linalg.norm(BC) + 1e-9)
        return float(np.degrees(np.arccos(np.clip(cos_angle, -1, 1))))

    def _get_curvature_distance(
        self, a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
    ) -> float:
        a, b, c = np.array(a), np.array(b), np.array(c)
        AC = c - a
        AC_len = np.linalg.norm(AC)
        if AC_len < 1e-9:
            return 0.0
        # Perpendicular distance from B to line AC
        perp = np.abs(np.cross(AC, a - b)) / AC_len
        if perp < 1e-9:
            return 0.0
        return float(perp / AC_len)

    def _process_mm_segment(
        self, segment: list[list[Any]]
    ) -> tuple[list[float], list[float], list[float]]:
        """
        Processes mouse movement segment. Returns directions, angles of curvature, and curvature distances.
        """
        directions = []
        angles_of_curvature = []
        curvature_distances = []
        for idx in range(len(segment) - 1):
            p1 = (
                (segment[idx][2], segment[idx][3])
                if segment[idx][0] == "mm"
                else (segment[idx][3], segment[idx][4])
            )
            p2 = (
                (segment[idx + 1][2], segment[idx + 1][3])
                if segment[idx + 1][0] == "mm"
                else (segment[idx + 1][3], segment[idx + 1][4])
            )
            directions.append(self._get_direction(p1, p2))

        for idx in range(len(segment) - 2):
            p1 = (
                (segment[idx][2], segment[idx][3])
                if segment[idx][0] == "mm"
                else (segment[idx][3], segment[idx][4])
            )
            p2 = (
                (segment[idx + 1][2], segment[idx + 1][3])
                if segment[idx + 1][0] == "mm"
                else (segment[idx + 1][3], segment[idx + 1][4])
            )
            p3 = (
                (segment[idx + 2][2], segment[idx + 2][3])
                if segment[idx + 2][0] == "mm"
                else (segment[idx + 2][3], segment[idx + 2][4])
            )
            angles_of_curvature.append(self._get_angle_of_curvature(p1, p2, p3))
            curvature_distances.append(self._get_curvature_distance(p1, p2, p3))

        return (
            directions,
            angles_of_curvature,
            curvature_distances,
        )

    def _process_mm_bursts(self) -> dict[str, tuple[float, float, float, float]]:
        """
        Processes mouse movement bursts. Returns -1 for all stats if no mouse movement events.
        mm event: ("mm", element_id, x, y, timestamp)
        """
        if not self.event_counts["mm"]:
            return {
                "directions": (-1, -1, -1, -1),
                "angles_of_curvature": (-1, -1, -1, -1),
                "curvature_distances": (-1, -1, -1, -1),
            }

        bursts = self.group_bursts(["mm", "md", "mu"], self.max_time_interval)
        segments: list[list[list[Any]]] = []
        for burst in bursts:
            segment = []
            md_seen = False

            for event in burst:
                if md_seen and event[0] != "mu":
                    # New segment terminated by click
                    valid_seg = self._is_valid_segment(segment)
                    if valid_seg is not None:
                        segments.append(valid_seg)

                    segment = []
                    md_seen = False

                segment.append(event)
                if event[0] == "md":
                    md_seen = True
                elif event[0] == "mu" and md_seen:
                    # New segment terminated by click
                    valid_seg = self._is_valid_segment(segment)
                    if valid_seg is not None:
                        segments.append(valid_seg)
                    segment = []
                    md_seen = False

            valid_seg = self._is_valid_segment(segment)
            if valid_seg is not None:
                segments.append(valid_seg)

        directions = []
        angles_of_curvature = []
        curvature_distances = []
        for segment in segments:
            new_directions, new_angles_of_curvature, new_curvature_distances = (
                self._process_mm_segment(segment)
            )
            directions.extend(new_directions)
            angles_of_curvature.extend(new_angles_of_curvature)
            curvature_distances.extend(new_curvature_distances)
        return {
            "directions": (
                self._get_stats(directions) if len(directions) > 0 else (-1, -1, -1, -1)
            ),
            "angles_of_curvature": (
                self._get_stats(angles_of_curvature)
                if len(angles_of_curvature) > 0
                else (-1, -1, -1, -1)
            ),
            "curvature_distances": (
                self._get_stats(curvature_distances)
                if len(curvature_distances) > 0
                else (-1, -1, -1, -1)
            ),
        }

    def _get_keypress_latencies(
        self,
        events: list[tuple[str, str, bool, float]],
    ) -> tuple[list[float], list[float], bool, bool]:
        """
        Extract interkey and hold latencies from keyboard events.

        Args:
            events (list[tuple[str, str, str, bool, float]]): List of keypress events
                event_type: "ku" for keyup or "kd" for keydown
                element_id: the element id of the keypress event
                key: the key identifier
                repeat: boolean indicating if this is a repeat event
                timestamp: timestamp in milliseconds (or any time unit)

        Returns:
            (tuple[list[float], list[float], bool, bool]): (interkey_latencies, hold_latencies, dangling_keydown, dangling_keyup)
                interkey_latencies: list of latencies between keyup and next keydown
                hold_latencies: list of latencies between first keydown and keyup for each key
                dangling_keydown: boolean indicating if there is a dangling keydown event
                dangling_keyup: boolean indicating if there is a dangling keyup event
        """
        interkey_latencies = []
        hold_latencies = []
        dangling_keydown = False
        dangling_keyup = False

        # Track the first keydown timestamp for each key currently being held
        key_press_start = {}

        # Track the last keyup timestamp
        last_keyup_time = None

        for event_type, element_id, key, repeat, timestamp in events:
            if event_type == "kd":
                # Calculate interkey latency (time since last keyup)
                if last_keyup_time is not None:
                    interkey_latencies.append(timestamp - last_keyup_time)
                    last_keyup_time = None  # Reset after calculating

                # Track first keydown for hold latency
                # Only record if this key isn't already being held
                if key not in key_press_start and not repeat:
                    key_press_start[key] = timestamp

            elif event_type == "ku":
                # Calculate hold latency
                if key in key_press_start:
                    hold_latencies.append(timestamp - key_press_start[key])
                    key_press_start.pop(key)
                else:
                    dangling_keyup = True

                # Track this keyup for interkey latency calculation
                last_keyup_time = timestamp

        if key_press_start:
            dangling_keydown = True

        return interkey_latencies, hold_latencies, dangling_keydown, dangling_keyup

    def _process_keypress_bursts(
        self,
    ) -> dict[str, tuple[float, float, float, float] | bool]:
        """Processes keypress bursts."""
        key_events = [e for e in self.events if e[0] in ["kd", "ku"]]

        interkey_latencies, hold_latencies, dangling_keydown, dangling_keyup = (
            self._get_keypress_latencies(key_events)
        )

        # Remove outliers
        def _remove_iqr_outliers(values: list[float]) -> list[float]:
            if len(values) < 4:
                return values

            q1, q3 = np.percentile(values, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            return [v for v in values if lower_bound <= v <= upper_bound]

        # 2000ms is way too long to not be an outlier for interkey latency
        interkey_latencies = [
            v for v in _remove_iqr_outliers(interkey_latencies) if v <= 2000
        ]
        hold_latencies = _remove_iqr_outliers(hold_latencies)

        return {
            "interkey": (
                self._get_stats(interkey_latencies)
                if len(interkey_latencies) > 0
                else (-1, -1, -1, -1)
            ),
            "hold": (
                self._get_stats(hold_latencies)
                if len(hold_latencies) > 0
                else (-1, -1, -1, -1)
            ),
            "dangling_keydown": dangling_keydown,
            "dangling_keyup": dangling_keyup,
        }

    def extract_feature_vector(self) -> list[float]:
        if self.feature_vector is not None:
            return self.feature_vector

        fv = []
        fv.append(len(self.event_counts["mm"]))
        mm_stats = self._process_mm_bursts()
        if mm_stats["directions"] == (-1, -1, -1, -1):
            fv.append(0)
        else:
            fv.append(1)
        fv.extend(mm_stats["directions"])
        fv.extend(mm_stats["angles_of_curvature"])
        fv.extend(mm_stats["curvature_distances"])

        for mouse_button in range(5):
            # Mouse button presence
            if (
                mouse_button not in self.mouse_down_counts
                or not self.mouse_down_counts[mouse_button]
            ) and (
                mouse_button not in self.mouse_up_counts
                or not self.mouse_up_counts[mouse_button]
            ):
                fv.append(0)
            else:
                fv.append(1)

            # Mouse button down-up ratio
            fv.append(
                self._get_ratio(
                    len(self.mouse_down_counts[mouse_button]),
                    len(self.mouse_up_counts[mouse_button]),
                )
            )

        # Scroll features
        fv.append(1 if len(self.event_counts["sc"]) > 0 else 0)
        fv.append(1 if len(self.event_counts["se"]) > 0 else 0)
        scroll_stats = self._process_scroll_bursts()
        fv.extend(scroll_stats["distance"])
        fv.extend(scroll_stats["time"])

        # Presence of keypresses (requires both down and up)
        keypress_presence = (
            len(self.key_down_counts) > 0
            and any(len(v) > 0 for v in self.key_down_counts.values())
            and len(self.key_up_counts) > 0
            and any(len(v) > 0 for v in self.key_up_counts.values())
        )

        fv.append(1 if keypress_presence else 0)

        if keypress_presence:
            keypress_stats = self._process_keypress_bursts()
            fv.extend(keypress_stats["interkey"])
            fv.extend(keypress_stats["hold"])
            fv.append(1 if keypress_stats["dangling_keydown"] else 0)
            fv.append(1 if keypress_stats["dangling_keyup"] else 0)
        else:
            fv += [-1] * 10

        # Keyup keydown ratio
        # No point in including this since it's possible that there are more keydown than keyup due to holding down the key
        # fv.append(self._get_ratio(len(self.key_up_counts), len(self.key_down_counts)))

        # Backspace/delete keypress statistics
        if not keypress_presence:
            fv += [-1] * 2
        else:
            num_typing_mistakes = len(self.key_down_counts["Backspace"]) + len(
                self.key_down_counts["Delete"]
            )
            fv += [
                num_typing_mistakes,
                num_typing_mistakes
                / sum(len(v) for v in self.key_down_counts.values()),
            ]

        fv.append(1 if len(self.event_counts["p"]) > 0 else 0)
        fv.append(len(self.event_counts["i"]))
        fv.append(len(self.event_counts["c"]))

        # Maybe a feature that somehow models the relationship between thinking intervals and action intervals (time between bursts and time between actions within a burst)

        self.feature_vector = fv
        return fv


class FingerprintFV:
    def __init__(self, feature_vector: list[float] | None = None):
        self.config_files_path = f"{PROJECT_ROOT}/features"
        self.X_FORWARDED_FOR_IP_HEADER_STR = "X-Forwarded-For"
        self.USER_AGENT_HEADER_STR = "User-Agent"
        self.SITE_STR = "https://agentic-ai-news.com/"
        self.load_config_lists()
        if feature_vector is not None:
            self.parse_feature_vector(feature_vector)

    def parse_feature_vector(self, feature_vector: list[float]):
        # Single-value features: extract first element
        self.audio = feature_vector[BROWSER_FEATURE_INDICES["audio"]["start"]]
        self.color_depth = feature_vector[
            BROWSER_FEATURE_INDICES["colorDepth"]["start"]
        ]
        self.contrast = feature_vector[BROWSER_FEATURE_INDICES["contrast"]["start"]]
        self.cookies_enabled = feature_vector[
            BROWSER_FEATURE_INDICES["cookiesEnabled"]["start"]
        ]
        self.device_memory = feature_vector[
            BROWSER_FEATURE_INDICES["deviceMemory"]["start"]
        ]
        self.forced_colors = feature_vector[
            BROWSER_FEATURE_INDICES["forcedColors"]["start"]
        ]
        self.hw_concurrency = feature_vector[
            BROWSER_FEATURE_INDICES["hardwareConcurrency"]["start"]
        ]
        self.hdr = feature_vector[BROWSER_FEATURE_INDICES["hdr"]["start"]]
        self.indexed_db = feature_vector[BROWSER_FEATURE_INDICES["indexedDB"]["start"]]
        self.inverted_colors = feature_vector[
            BROWSER_FEATURE_INDICES["invertedColors"]["start"]
        ]
        self.local_storage = feature_vector[
            BROWSER_FEATURE_INDICES["localStorage"]["start"]
        ]
        self.monochrome = feature_vector[BROWSER_FEATURE_INDICES["monochrome"]["start"]]
        self.open_db = feature_vector[BROWSER_FEATURE_INDICES["openDB"]["start"]]
        self.reduced_motion = feature_vector[
            BROWSER_FEATURE_INDICES["reducedMotion"]["start"]
        ]
        self.session_storage = feature_vector[
            BROWSER_FEATURE_INDICES["sessionStorage"]["start"]
        ]
        self.plugins = feature_vector[
            BROWSER_FEATURE_INDICES["plugins"]["start"] : BROWSER_FEATURE_INDICES[
                "plugins"
            ]["end"]
        ]
        self.color_gamut = feature_vector[
            BROWSER_FEATURE_INDICES["colorGamut"]["start"] : BROWSER_FEATURE_INDICES[
                "colorGamut"
            ]["end"]
        ]
        self.platform = feature_vector[
            BROWSER_FEATURE_INDICES["platform"]["start"] : BROWSER_FEATURE_INDICES[
                "platform"
            ]["end"]
        ]
        self.timezone = feature_vector[
            BROWSER_FEATURE_INDICES["timezone"]["start"] : BROWSER_FEATURE_INDICES[
                "timezone"
            ]["end"]
        ]
        self.vendor = feature_vector[
            BROWSER_FEATURE_INDICES["vendor"]["start"] : BROWSER_FEATURE_INDICES[
                "vendor"
            ]["end"]
        ]
        self.vendor_flavors = feature_vector[
            BROWSER_FEATURE_INDICES["vendorFlavors"]["start"] : BROWSER_FEATURE_INDICES[
                "vendorFlavors"
            ]["end"]
        ]
        self.fonts = feature_vector[
            BROWSER_FEATURE_INDICES["fonts"]["start"] : BROWSER_FEATURE_INDICES[
                "fonts"
            ]["end"]
        ]
        self.languages = feature_vector[
            BROWSER_FEATURE_INDICES["languages"]["start"] : BROWSER_FEATURE_INDICES[
                "languages"
            ]["end"]
        ]
        self.os_cpu = feature_vector[
            BROWSER_FEATURE_INDICES["osCpu"]["start"] : BROWSER_FEATURE_INDICES[
                "osCpu"
            ]["end"]
        ]
        self.screen_resolution = feature_vector[
            BROWSER_FEATURE_INDICES["screenResolution_0"][
                "start"
            ] : BROWSER_FEATURE_INDICES["screenResolution_1"]["end"]
        ]
        self.screen_frame = feature_vector[
            BROWSER_FEATURE_INDICES["screenFrame_0"]["start"] : BROWSER_FEATURE_INDICES[
                "screenFrame_3"
            ]["end"]
        ]
        self.touch_support = feature_vector[
            BROWSER_FEATURE_INDICES["maxTouchPoints"][
                "start"
            ] : BROWSER_FEATURE_INDICES["touchStart"]["end"]
        ]
        self.math = feature_vector[
            BROWSER_FEATURE_INDICES["acos"]["start"] : BROWSER_FEATURE_INDICES[
                "tanhPf"
            ]["end"]
        ]
        self.font_preferences = feature_vector[
            BROWSER_FEATURE_INDICES["fontApple"]["start"] : BROWSER_FEATURE_INDICES[
                "fontSystem"
            ]["end"]
        ]

    def parse_traffic_data(self, req_headers, req_body):
        self.parse_failed = False
        self.parse_features(req_headers, req_body)

    def load_json(self, json_name):
        with open(json_name) as f:
            d = orjson.loads(f.read())
        return d

    def load_config_lists(self):
        self.list_config = {}
        self.list_config["plugins"] = self.read_list("plugins")
        self.list_config["colorGamut"] = self.read_list("colorGamut")
        self.list_config["platform"] = self.read_list("platform")
        self.list_config["timezone"] = self.read_list("timezone")
        self.list_config["vendor"] = self.read_list("vendor")
        self.list_config["fonts"] = self.read_list("fonts")
        self.list_config["languages"] = self.read_list("languages")
        self.list_config["vendorFlavors"] = self.read_list("vendorFlavors")
        self.list_config["osCpu"] = self.read_list("osCpu")
        self.touch_support_features = self.read_list("touchSupport")
        self.math_features = self.read_list("math")
        self.font_preferences_features = self.read_list("fontPreferences")

    def read_list(self, list_name):
        with open(os.path.join(self.config_files_path, f"{list_name}.txt")) as f:
            list_items = sorted(f.read().splitlines())
        return list_items

    def extract_feature_vector(self) -> list[float]:
        fv = []
        fv.append(self.audio)
        fv.append(self.color_depth)
        fv.append(self.contrast)

        fv.append(self.cookies_enabled)
        fv.append(self.device_memory)
        fv.append(self.forced_colors)
        fv.append(self.hw_concurrency)

        fv.append(self.hdr)
        fv.append(self.indexed_db)
        fv.append(self.inverted_colors)
        fv.append(self.local_storage)
        fv.append(self.monochrome)
        fv.append(self.open_db)
        fv.append(self.reduced_motion)
        fv.append(self.session_storage)

        fv.extend(self.plugins)
        fv.extend(self.color_gamut)
        fv.extend(self.platform)
        fv.extend(self.timezone)
        fv.extend(self.vendor)
        fv.extend(self.vendor_flavors)
        fv.extend(self.fonts)
        fv.extend(self.languages)
        fv.extend(self.os_cpu)
        fv.extend(self.screen_resolution)
        fv.extend(self.screen_frame)
        fv.extend(self.touch_support)
        fv.extend(self.math)
        fv.extend(self.font_preferences)

        return fv

    def extract_ip_address(self, r_headers: dict[str, str]):
        return r_headers.get(self.X_FORWARDED_FOR_IP_HEADER_STR, "")

    def extract_user_agent(self, r_headers: dict[str, str]):
        return r_headers.get(self.USER_AGENT_HEADER_STR, "")

    def parse_features(self, req_headers: dict[str, str], req_body: dict[str, str]):
        fpjs_res = req_body["result"]
        fpjs_components = fpjs_res["components"]

        self.ip_address = self.extract_ip_address(req_headers)
        self.user_agent_string = self.extract_user_agent(req_headers)
        self.traffic_source = req_body["sourcePage"]
        if self.SITE_STR not in self.traffic_source:
            self.parse_failed = True

        self.audio = self.sanitize_float(fpjs_components["audio"])
        self.color_depth = self.sanitize_float(fpjs_components["colorDepth"])
        self.color_gamut = self.sanitize_string_list(
            fpjs_components["colorGamut"], "colorGamut"
        )
        self.contrast = self.sanitize_float(fpjs_components["contrast"])
        self.cookies_enabled = self.sanitize_float(fpjs_components["cookiesEnabled"])
        self.device_memory = self.sanitize_float(fpjs_components["deviceMemory"])
        self.forced_colors = self.sanitize_float(fpjs_components["forcedColors"])
        self.hw_concurrency = self.sanitize_float(
            fpjs_components["hardwareConcurrency"]
        )
        self.hdr = self.sanitize_float(fpjs_components["hdr"])
        self.indexed_db = self.sanitize_float(fpjs_components["indexedDB"])
        self.inverted_colors = self.sanitize_float(fpjs_components["invertedColors"])
        self.local_storage = self.sanitize_float(fpjs_components["localStorage"])
        self.monochrome = self.sanitize_float(fpjs_components["monochrome"])
        self.open_db = self.sanitize_float(fpjs_components["openDatabase"])
        self.platform = self.sanitize_string_list(
            fpjs_components["platform"], "platform"
        )
        self.reduced_motion = self.sanitize_float(fpjs_components["reducedMotion"])
        self.session_storage = self.sanitize_float(fpjs_components["sessionStorage"])
        self.timezone = self.sanitize_string_list(
            fpjs_components["timezone"], "timezone"
        )
        self.os_cpu = self.sanitize_string_list(fpjs_components["osCpu"], "osCpu")
        self.vendor = self.sanitize_string_list(fpjs_components["vendor"], "vendor")
        self.vendor_flavors = self.sanitize_string_list(
            fpjs_components["vendorFlavors"], "vendorFlavors"
        )
        self.fonts = self.sanitize_string_list(fpjs_components["fonts"], "fonts")
        self.languages = self.sanitize_string_list(
            fpjs_components["languages"], "languages"
        )
        self.plugins = self.sanitize_plugins(fpjs_components["plugins"])
        self.screen_resolution = self.sanitize_screen_resolution(
            fpjs_components["screenResolution"]
        )
        self.screen_frame = self.sanitize_screen_frame(fpjs_components["screenFrame"])
        self.touch_support = self.sanitize_touch_support(
            fpjs_components["touchSupport"]
        )
        self.math = self.sanitize_math(fpjs_components["math"])
        self.font_preferences = self.sanitize_font_preferences(
            fpjs_components["fontPreferences"]
        )

    def check_components(
        self, component: dict[str, Any], feature_name: str
    ) -> set[str]:
        if feature_name == "touchSupport":
            return component.keys() ^ set(self.touch_support_features)
        elif feature_name == "math":
            return component.keys() ^ set(self.math_features)
        elif feature_name == "fontPreferences":
            return component.keys() ^ set(self.font_preferences_features)
        else:
            raise ValueError(f"Unknown feature name: {feature_name}")

    def sanitize_screen_resolution(self, screen_res_component):
        # Hacky
        if "value" in screen_res_component and len(screen_res_component["value"]) == 2:
            return screen_res_component["value"]
        return [-1] * 2

    def sanitize_screen_frame(self, screen_frame_component):
        # Hacky
        if (
            "value" in screen_frame_component
            and len(screen_frame_component["value"]) == 4
        ):
            return screen_frame_component["value"]
        return [-1] * 4

    def sanitize_touch_support(self, touch_support_component):
        # Hacky
        recorded_touch_support_features = []
        if "value" in touch_support_component:
            touch_support_feature_keys = sorted(
                list(touch_support_component["value"].keys())
            )
            new_components = self.check_components(
                touch_support_component["value"], "touchSupport"
            )
            if new_components:
                print(f"New components: {new_components}")
            if touch_support_feature_keys == self.touch_support_features:
                for f, v in touch_support_component["value"].items():
                    if f in self.touch_support_features:
                        if isinstance(v, bool):
                            recorded_touch_support_features.append(1 if v else 0)
                        else:
                            recorded_touch_support_features.append(v)

        if len(recorded_touch_support_features) == len(self.touch_support_features):
            return recorded_touch_support_features

        return [-1] * len(self.touch_support_features)

    def sanitize_math(self, math_component):
        # Hacky
        recorded_math_features = []
        if "value" in math_component:
            math_feature_keys = sorted(list(math_component["value"].keys()))
            new_components = self.check_components(math_component["value"], "math")
            if new_components:
                print(f"New components: {new_components}")
            if math_feature_keys == self.math_features:
                for f in self.math_features:
                    # In the future, can do .get(f, -1) to handle missing features
                    recorded_math_features.append(math_component["value"][f])

        if len(recorded_math_features) == len(self.math_features):
            return recorded_math_features

        return [-1] * len(self.math_features)

    def sanitize_font_preferences(self, font_preferences_component):
        # Hacky
        recorded_font_preferences_features = []
        if "value" in font_preferences_component:
            font_preferences_feature_keys = sorted(
                list(font_preferences_component["value"].keys())
            )
            new_components = self.check_components(
                font_preferences_component["value"], "fontPreferences"
            )
            if new_components:
                print(f"New components: {new_components}")
            if font_preferences_feature_keys == self.font_preferences_features:
                for f in self.font_preferences_features:
                    recorded_font_preferences_features.append(
                        font_preferences_component["value"][f]
                    )

        if len(recorded_font_preferences_features) == len(
            self.font_preferences_features
        ):
            return recorded_font_preferences_features

        return [-1] * len(self.font_preferences_features)

    def sanitize_plugins(self, plugins_component) -> list[float]:
        component_list = self.list_config["plugins"]
        onehot_feature = [0] * (len(component_list) + 1)

        if "value" in plugins_component:
            # List of dicts
            for plugin in plugins_component["value"]:
                if "name" not in plugin:
                    continue
                name = plugin["name"]
                onehot_feature = self.set_onehot(onehot_feature, component_list, name)
        return onehot_feature

    def sanitize_canvas(self, canvas_component, feature):
        if "value" in canvas_component:
            if feature in canvas_component["value"]:
                return canvas_component["value"][feature]
            return ""
        return ""

    def sanitize_float(self, float_component: dict[Any, Any]) -> float:
        """
        Sanitize the float component.

        Args:
            float_component (dict[Any, Any]): The float component to sanitize

        Returns:
            (float): The sanitized float value. If the value is not found, return -1.
        """
        if "value" in float_component:
            return float(float_component["value"])
        return float(-1)

    def sanitize_string_list(
        self, string_list_component: dict[Any, Any], component_name: str
    ) -> list[int]:
        """
        Sanitize the string list component. The return value will have as many
        dimensions as possible values for this component.

        Args:
            string_list_component (dict[Any, Any]): The string list component to sanitize
            component_name (str): The name of the component to sanitize

        Returns:
            (list[int]): The sanitized string list as a one-hot encoded list
        """
        # if component_name == 'plugins':
        #    return self.sanitize_plugin_component(string_list_component)

        component_list = self.list_config[component_name]

        onehot_feature = [0] * (len(component_list) + 1)

        if "value" in string_list_component:
            if isinstance(string_list_component["value"], list):
                for val in string_list_component["value"]:
                    if isinstance(val, list):
                        for v in val:
                            onehot_feature = self.set_onehot(
                                onehot_feature, component_list, v
                            )
                    elif isinstance(val, dict) and "name" in val:
                        onehot_feature = self.set_onehot(
                            onehot_feature, component_list, val["name"]
                        )
                    else:
                        onehot_feature = self.set_onehot(
                            onehot_feature, component_list, val
                        )
            else:
                # string_list_component['value'] must be a string
                onehot_feature = self.set_onehot(
                    onehot_feature, component_list, string_list_component["value"]
                )

        return onehot_feature

    def set_onehot(self, onehot_feature, component_list, v):
        if v in component_list:
            onehot_feature[component_list.index(v)] = 1
        else:
            print(f"{v} not in {component_list}")
            onehot_feature[-1] = 1
        return onehot_feature
