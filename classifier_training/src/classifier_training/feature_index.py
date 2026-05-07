import os
from typing import Any

import dotenv

dotenv.load_dotenv()
PROJECT_ROOT = os.getenv("PROJECT_ROOT")

from classifier_training.types import FeatureType

"""
BROWSER FEATURE INDICES
"""

BROWSER_FEATURE_INDICES: dict[str, dict[str, int]] = {}
BROWSER_FEATURE_INDICES["audio"] = {"start": 0, "end": 1}
BROWSER_FEATURE_INDICES["colorDepth"] = {"start": 1, "end": 2}
BROWSER_FEATURE_INDICES["contrast"] = {"start": 2, "end": 3}
BROWSER_FEATURE_INDICES["cookiesEnabled"] = {"start": 3, "end": 4}
BROWSER_FEATURE_INDICES["deviceMemory"] = {"start": 4, "end": 5}
BROWSER_FEATURE_INDICES["forcedColors"] = {"start": 5, "end": 6}
BROWSER_FEATURE_INDICES["hardwareConcurrency"] = {"start": 6, "end": 7}
BROWSER_FEATURE_INDICES["hdr"] = {"start": 7, "end": 8}
BROWSER_FEATURE_INDICES["indexedDB"] = {"start": 8, "end": 9}
BROWSER_FEATURE_INDICES["invertedColors"] = {"start": 9, "end": 10}
BROWSER_FEATURE_INDICES["localStorage"] = {"start": 10, "end": 11}
BROWSER_FEATURE_INDICES["monochrome"] = {"start": 11, "end": 12}
BROWSER_FEATURE_INDICES["openDB"] = {"start": 12, "end": 13}
BROWSER_FEATURE_INDICES["reducedMotion"] = {"start": 13, "end": 14}
BROWSER_FEATURE_INDICES["sessionStorage"] = {"start": 14, "end": 15}
BROWSER_FEATURE_INDICES["plugins"] = {"start": 15, "end": 25}
BROWSER_FEATURE_INDICES["colorGamut"] = {"start": 25, "end": 29}
BROWSER_FEATURE_INDICES["platform"] = {"start": 29, "end": 42}
BROWSER_FEATURE_INDICES["timezone"] = {"start": 42, "end": 186}
BROWSER_FEATURE_INDICES["vendor"] = {"start": 186, "end": 190}
BROWSER_FEATURE_INDICES["vendorFlavors"] = {"start": 190, "end": 195}
BROWSER_FEATURE_INDICES["fonts"] = {"start": 195, "end": 248}
BROWSER_FEATURE_INDICES["languages"] = {"start": 248, "end": 369}
BROWSER_FEATURE_INDICES["osCpu"] = {"start": 369, "end": 378}
BROWSER_FEATURE_INDICES["screenResolution_0"] = {"start": 378, "end": 379}
BROWSER_FEATURE_INDICES["screenResolution_1"] = {"start": 379, "end": 380}
BROWSER_FEATURE_INDICES["screenFrame_0"] = {"start": 380, "end": 381}
BROWSER_FEATURE_INDICES["screenFrame_1"] = {"start": 381, "end": 382}
BROWSER_FEATURE_INDICES["screenFrame_2"] = {"start": 382, "end": 383}
BROWSER_FEATURE_INDICES["screenFrame_3"] = {"start": 383, "end": 384}
BROWSER_FEATURE_INDICES["maxTouchPoints"] = {"start": 384, "end": 385}
BROWSER_FEATURE_INDICES["touchEvent"] = {"start": 385, "end": 386}
BROWSER_FEATURE_INDICES["touchStart"] = {"start": 386, "end": 387}
BROWSER_FEATURE_INDICES["acos"] = {"start": 387, "end": 388}
BROWSER_FEATURE_INDICES["acosh"] = {"start": 388, "end": 389}
BROWSER_FEATURE_INDICES["acoshPf"] = {"start": 389, "end": 390}
BROWSER_FEATURE_INDICES["asin"] = {"start": 390, "end": 391}
BROWSER_FEATURE_INDICES["asinh"] = {"start": 391, "end": 392}
BROWSER_FEATURE_INDICES["asinhPf"] = {"start": 392, "end": 393}
BROWSER_FEATURE_INDICES["atan"] = {"start": 393, "end": 394}
BROWSER_FEATURE_INDICES["atanh"] = {"start": 394, "end": 395}
BROWSER_FEATURE_INDICES["atanhPf"] = {"start": 395, "end": 396}
BROWSER_FEATURE_INDICES["cos"] = {"start": 396, "end": 397}
BROWSER_FEATURE_INDICES["cosh"] = {"start": 397, "end": 398}
BROWSER_FEATURE_INDICES["coshPf"] = {"start": 398, "end": 399}
BROWSER_FEATURE_INDICES["exp"] = {"start": 399, "end": 400}
BROWSER_FEATURE_INDICES["expm1"] = {"start": 400, "end": 401}
BROWSER_FEATURE_INDICES["expm1Pf"] = {"start": 401, "end": 402}
BROWSER_FEATURE_INDICES["log1p"] = {"start": 402, "end": 403}
BROWSER_FEATURE_INDICES["log1pPf"] = {"start": 403, "end": 404}
BROWSER_FEATURE_INDICES["powPI"] = {"start": 404, "end": 405}
BROWSER_FEATURE_INDICES["sin"] = {"start": 405, "end": 406}
BROWSER_FEATURE_INDICES["sinh"] = {"start": 406, "end": 407}
BROWSER_FEATURE_INDICES["sinhPf"] = {"start": 407, "end": 408}
BROWSER_FEATURE_INDICES["tan"] = {"start": 408, "end": 409}
BROWSER_FEATURE_INDICES["tanh"] = {"start": 409, "end": 410}
BROWSER_FEATURE_INDICES["tanhPf"] = {"start": 410, "end": 411}
BROWSER_FEATURE_INDICES["fontApple"] = {"start": 411, "end": 412}
BROWSER_FEATURE_INDICES["fontDefault"] = {"start": 412, "end": 413}
BROWSER_FEATURE_INDICES["fontMin"] = {"start": 413, "end": 414}
BROWSER_FEATURE_INDICES["fontMono"] = {"start": 414, "end": 415}
BROWSER_FEATURE_INDICES["fontSans"] = {"start": 415, "end": 416}
BROWSER_FEATURE_INDICES["fontSerif"] = {"start": 416, "end": 417}
BROWSER_FEATURE_INDICES["fontSystem"] = {"start": 417, "end": 418}


"""
BEHAVIORAL FEATURE INDICES
"""

BEHAVIORAL_FEATURE_INDICES: dict[str, dict[str, int]] = {}
# Mouse movement features
BEHAVIORAL_FEATURE_INDICES["num_mouse_movements"] = {"start": 0, "end": 1}
BEHAVIORAL_FEATURE_INDICES["mm_presence"] = {"start": 1, "end": 2}
BEHAVIORAL_FEATURE_INDICES["mm_directions_mean"] = {"start": 2, "end": 3}
BEHAVIORAL_FEATURE_INDICES["mm_directions_median"] = {"start": 3, "end": 4}
BEHAVIORAL_FEATURE_INDICES["mm_directions_range"] = {"start": 4, "end": 5}
BEHAVIORAL_FEATURE_INDICES["mm_directions_stdev"] = {"start": 5, "end": 6}
BEHAVIORAL_FEATURE_INDICES["mm_angles_of_curvature_mean"] = {"start": 6, "end": 7}
BEHAVIORAL_FEATURE_INDICES["mm_angles_of_curvature_median"] = {"start": 7, "end": 8}
BEHAVIORAL_FEATURE_INDICES["mm_angles_of_curvature_range"] = {"start": 8, "end": 9}
BEHAVIORAL_FEATURE_INDICES["mm_angles_of_curvature_stdev"] = {"start": 9, "end": 10}
BEHAVIORAL_FEATURE_INDICES["mm_curvature_distances_mean"] = {"start": 10, "end": 11}
BEHAVIORAL_FEATURE_INDICES["mm_curvature_distances_median"] = {"start": 11, "end": 12}
BEHAVIORAL_FEATURE_INDICES["mm_curvature_distances_range"] = {"start": 12, "end": 13}
BEHAVIORAL_FEATURE_INDICES["mm_curvature_distances_stdev"] = {"start": 13, "end": 14}

# Mouse button features (5 buttons: 0-4)
# Each button has: presence, down_up_ratio
BEHAVIORAL_FEATURE_INDICES["mouse_button_0_presence"] = {"start": 14, "end": 15}
BEHAVIORAL_FEATURE_INDICES["mouse_button_0_down_up_ratio"] = {"start": 15, "end": 16}
BEHAVIORAL_FEATURE_INDICES["mouse_button_1_presence"] = {"start": 16, "end": 17}
BEHAVIORAL_FEATURE_INDICES["mouse_button_1_down_up_ratio"] = {"start": 17, "end": 18}
BEHAVIORAL_FEATURE_INDICES["mouse_button_2_presence"] = {"start": 18, "end": 19}
BEHAVIORAL_FEATURE_INDICES["mouse_button_2_down_up_ratio"] = {"start": 19, "end": 20}
BEHAVIORAL_FEATURE_INDICES["mouse_button_3_presence"] = {"start": 20, "end": 21}
BEHAVIORAL_FEATURE_INDICES["mouse_button_3_down_up_ratio"] = {"start": 21, "end": 22}
BEHAVIORAL_FEATURE_INDICES["mouse_button_4_presence"] = {"start": 22, "end": 23}
BEHAVIORAL_FEATURE_INDICES["mouse_button_4_down_up_ratio"] = {"start": 23, "end": 24}

# Scroll features
BEHAVIORAL_FEATURE_INDICES["scroll_presence"] = {"start": 24, "end": 25}
BEHAVIORAL_FEATURE_INDICES["scroll_end_presence"] = {"start": 25, "end": 26}
BEHAVIORAL_FEATURE_INDICES["scroll_distance_mean"] = {"start": 26, "end": 27}
BEHAVIORAL_FEATURE_INDICES["scroll_distance_median"] = {"start": 27, "end": 28}
BEHAVIORAL_FEATURE_INDICES["scroll_distance_range"] = {"start": 28, "end": 29}
BEHAVIORAL_FEATURE_INDICES["scroll_distance_stdev"] = {"start": 29, "end": 30}
BEHAVIORAL_FEATURE_INDICES["scroll_time_mean"] = {"start": 30, "end": 31}
BEHAVIORAL_FEATURE_INDICES["scroll_time_median"] = {"start": 31, "end": 32}
BEHAVIORAL_FEATURE_INDICES["scroll_time_range"] = {"start": 32, "end": 33}
BEHAVIORAL_FEATURE_INDICES["scroll_time_stdev"] = {"start": 33, "end": 34}

# Keypress features
BEHAVIORAL_FEATURE_INDICES["keypress_presence"] = {"start": 34, "end": 35}
BEHAVIORAL_FEATURE_INDICES["interkey_latency_mean"] = {"start": 35, "end": 36}
BEHAVIORAL_FEATURE_INDICES["interkey_latency_median"] = {"start": 36, "end": 37}
BEHAVIORAL_FEATURE_INDICES["interkey_latency_range"] = {"start": 37, "end": 38}
BEHAVIORAL_FEATURE_INDICES["interkey_latency_stdev"] = {"start": 38, "end": 39}
BEHAVIORAL_FEATURE_INDICES["hold_latency_mean"] = {"start": 39, "end": 40}
BEHAVIORAL_FEATURE_INDICES["hold_latency_median"] = {"start": 40, "end": 41}
BEHAVIORAL_FEATURE_INDICES["hold_latency_range"] = {"start": 41, "end": 42}
BEHAVIORAL_FEATURE_INDICES["hold_latency_stdev"] = {"start": 42, "end": 43}
BEHAVIORAL_FEATURE_INDICES["dangling_keydown"] = {"start": 43, "end": 44}
BEHAVIORAL_FEATURE_INDICES["dangling_keyup"] = {"start": 44, "end": 45}
BEHAVIORAL_FEATURE_INDICES["num_typing_mistakes"] = {"start": 45, "end": 46}
BEHAVIORAL_FEATURE_INDICES["typing_mistakes_ratio"] = {"start": 46, "end": 47}

# Other event features
BEHAVIORAL_FEATURE_INDICES["paste_presence"] = {"start": 47, "end": 48}
BEHAVIORAL_FEATURE_INDICES["num_input_events"] = {"start": 48, "end": 49}
BEHAVIORAL_FEATURE_INDICES["num_change_events"] = {"start": 49, "end": 50}


def get_feature_name_list(feature_type: FeatureType) -> list[str]:
    assert feature_type in [FeatureType.BROWSER, FeatureType.BEHAVIORAL]

    feature_indices = (
        BROWSER_FEATURE_INDICES
        if feature_type == FeatureType.BROWSER
        else BEHAVIORAL_FEATURE_INDICES
    )
    feature_name_list = []
    for feature_name, start_stop_indices in feature_indices.items():
        start = start_stop_indices["start"]
        end = start_stop_indices["end"]
        feature_name_list += [feature_name for _ in range(end - start)]
    return feature_name_list


browser_feature_name_list = get_feature_name_list(FeatureType.BROWSER)
behavioral_feature_name_list = get_feature_name_list(FeatureType.BEHAVIORAL)
combined_feature_name_list = browser_feature_name_list + behavioral_feature_name_list

FEATURE_NAME_LIST = {
    FeatureType.BROWSER: browser_feature_name_list,
    FeatureType.BEHAVIORAL: behavioral_feature_name_list,
    FeatureType.COMBINED: combined_feature_name_list,
}

"""
COMBINED FEATURE INDICES
"""

COMBINED_FEATURE_INDICES = {
    **BROWSER_FEATURE_INDICES,
    **{
        key: {
            "start": val["start"] + len(browser_feature_name_list),
            "end": val["end"] + len(browser_feature_name_list),
        }
        for key, val in BEHAVIORAL_FEATURE_INDICES.items()
    },
}

FEATURE_INDICES: dict[FeatureType, dict[str, dict[str, int]]] = {
    FeatureType.BROWSER: BROWSER_FEATURE_INDICES,
    FeatureType.BEHAVIORAL: BEHAVIORAL_FEATURE_INDICES,
    FeatureType.COMBINED: COMBINED_FEATURE_INDICES,
}


def read_list(list_name):
    with open(os.path.join(PROJECT_ROOT, "features", f"{list_name}.txt")) as f:
        d = sorted(f.read().splitlines())
    d.append("unknown")
    return d


CATEGORIES: dict[str, list[str]] = {}
CATEGORIES["plugins"] = read_list("plugins")
CATEGORIES["vendorFlavors"] = read_list("vendorFlavors")
CATEGORIES["platform"] = read_list("platform")
CATEGORIES["timezone"] = read_list("timezone")
CATEGORIES["vendor"] = read_list("vendor")
CATEGORIES["colorGamut"] = read_list("colorGamut")
CATEGORIES["languages"] = read_list("languages")
CATEGORIES["fonts"] = read_list("fonts")
CATEGORIES["osCpu"] = read_list("osCpu")


def get_feature_index(
    feature_type: FeatureType,
    feature_names: str | list[str],
    removed_indices: list[int] = [],
) -> dict[str, int]:
    assert feature_type in [
        FeatureType.BROWSER,
        FeatureType.BEHAVIORAL,
        FeatureType.COMBINED,
    ], f"Invalid feature type: {feature_type.name}"

    feature_name_list = FEATURE_NAME_LIST[feature_type].copy()
    categories = CATEGORIES.copy()

    removed_categories = {}
    if removed_indices:
        removed = sorted({int(i) for i in removed_indices})

        for removed_idx in removed:
            if feature_name_list[removed_idx] in categories:
                if feature_name_list[removed_idx] not in removed_categories:
                    removed_categories[feature_name_list[removed_idx]] = []
                removed_categories[feature_name_list[removed_idx]].append(
                    removed_idx
                    - feature_name_list.index(feature_name_list[removed_idx])
                )

        feature_name_list = [
            v for i, v in enumerate(feature_name_list) if i not in removed
        ]
        for category_name in categories:
            if category_name in removed_categories:
                categories[category_name] = [
                    v
                    for i, v in enumerate(categories[category_name])
                    if i not in removed_categories[category_name]
                ]

    feature_indices = {}
    cur_feature_name = None
    for idx, name in enumerate(feature_name_list):
        if cur_feature_name != name:
            cur_feature_name = name
            feature_indices[name] = {"start": idx, "end": idx + 1}
        else:
            feature_indices[name]["end"] += 1

    if isinstance(feature_names, str):
        feature_names = [feature_names]

    res = {}
    for feature_name in feature_names:
        split_name = feature_name.split(": ", maxsplit=1)
        indices_name = split_name[0]
        value_name = split_name[1] if len(split_name) > 1 else None

        if indices_name not in feature_indices:
            if indices_name in FEATURE_INDICES[feature_type]:
                raise ValueError(f"Feature {feature_name} was removed")
            raise ValueError(
                f"Feature {feature_name} is not a valid {feature_type.name.lower()} feature"
            )

        res[feature_name] = feature_indices[indices_name]["start"]
        if value_name is not None:
            if indices_name in categories:
                res[feature_name] += categories[indices_name].index(value_name)
            else:
                assert (
                    indices_name not in CATEGORIES
                ), f"Feature {indices_name} is a categorical feature"
                res[feature_name] += int(value_name)
    return res


def get_feature_name(
    feature_type: FeatureType, indices: int | list[int], removed_indices: list[int] = []
) -> dict[int, str]:
    """
    Returns a dictionary mapping indices to feature names for a given index/list of indices.
    If a feature name spans multiple indices, the index within that feature is returned.
    Follows 0-based indexing.

    If `removed_indices` is provided, those indices are treated as removed from the
    flattened feature vector, and all subsequent indices are shifted down to fill
    the gaps. The returned mapping uses the (potentially shifted) indices passed
    in via `indices`.
    """
    assert feature_type in [
        FeatureType.BROWSER,
        FeatureType.BEHAVIORAL,
        FeatureType.COMBINED,
    ], f"Invalid feature type: {feature_type.name}"

    feature_name_list = FEATURE_NAME_LIST[feature_type].copy()
    assert all(
        0 <= i < len(feature_name_list) for i in removed_indices
    ), f"Removed indices must be within 0 to {len(feature_name_list) - 1} for {feature_type.name.lower()} features"

    categories = CATEGORIES.copy()
    removed_categories = {}
    if removed_indices:
        removed = sorted({int(i) for i in removed_indices})
        for removed_idx in removed:
            if feature_name_list[removed_idx] in categories:
                if feature_name_list[removed_idx] not in removed_categories:
                    removed_categories[feature_name_list[removed_idx]] = []
                removed_categories[feature_name_list[removed_idx]].append(
                    removed_idx
                    - feature_name_list.index(feature_name_list[removed_idx])
                )

        feature_name_list = [
            v for i, v in enumerate(feature_name_list) if i not in removed
        ]
        for category_name in categories:
            if category_name in removed_categories:
                categories[category_name] = [
                    v
                    for i, v in enumerate(categories[category_name])
                    if i not in removed_categories[category_name]
                ]

    if isinstance(indices, int):
        indices = [indices]

    res = {}
    for idx in indices:
        if idx >= len(feature_name_list) or idx < 0:
            raise ValueError(f"Index {idx} is out of feature indices range")

        feature_name = feature_name_list[idx]
        if feature_name in categories:  # Only for browser features
            local_idx = idx - feature_name_list.index(feature_name)
            res[idx] = f"{feature_name}: {categories[feature_name][local_idx]}"
        else:
            if feature_name_list.count(feature_name) > 1:
                local_idx = idx - feature_name_list.index(feature_name)
                res[idx] = f"{feature_name}: {local_idx}"
            else:
                res[idx] = feature_name
    return res


def get_labeled_feature_vector(
    feature_type: FeatureType,
    feature_vector: list[float],
    removed_indices: list[int] = [],
) -> dict[str, Any]:
    labeled_fv = {}
    for idx, val in enumerate(feature_vector):
        labeled_fv[get_feature_name(feature_type, idx, removed_indices)[idx]] = val
    return labeled_fv
