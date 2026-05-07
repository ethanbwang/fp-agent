from collections import defaultdict
from dataclasses import dataclass
import os
import traceback
from typing import Any

import numpy as np
import orjson
import psycopg2
from sklearn.model_selection import train_test_split

from classifier_training.data_preprocessing import preprocess_tuple
from classifier_training.featurizer import BehavioralFV, FingerprintFV


@dataclass(frozen=True)
class DataSource:
    """Metadata about the source of a feature vector."""

    website_version: str
    class_label: str
    task_name: str
    trial_index: int
    start_time: str
    end_time: str
    source_file: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "website_version": self.website_version,
            "class_label": self.class_label,
            "task_name": self.task_name,
            "trial_index": self.trial_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "source_file": self.source_file,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "DataSource":
        return DataSource(
            website_version=data["website_version"],
            class_label=data["class_label"],
            task_name=data["task_name"],
            trial_index=data["trial_index"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            source_file=data["source_file"],
        )


@dataclass
class RawFpjsData:
    """Raw fingerprint data."""

    req_headers: str
    req_body: str


@dataclass
class RawMmData:
    """Raw behavioral data."""

    req_headers: str
    req_body: str


@dataclass
class RawData:
    fpjs_data: list[RawFpjsData]
    behavioral_data: list[RawMmData]
    source: DataSource


@dataclass
class ProcessedData:
    fpjs_feature_vector: FingerprintFV
    behavioral_feature_vector: BehavioralFV
    source: DataSource


def save_raw_data(raw_data: dict[str, list[RawData]], filename: str) -> None:
    """Saves raw data to a file."""
    serialized_raw_data = {}
    for class_label, raw_data_entries in raw_data.items():
        serialized_raw_data[class_label] = []
        for raw_data_entry in raw_data_entries:
            serialized_raw_data[class_label].append(
                {
                    "fpjs_data": [
                        {
                            "req_headers": raw_fpjs_data.req_headers,
                            "req_body": raw_fpjs_data.req_body,
                        }
                        for raw_fpjs_data in raw_data_entry.fpjs_data
                    ],
                    "behavioral_data": [
                        {
                            "req_headers": raw_mm_data.req_headers,
                            "req_body": raw_mm_data.req_body,
                        }
                        for raw_mm_data in raw_data_entry.behavioral_data
                    ],
                    "source": raw_data_entry.source.to_dict(),
                }
            )

    with open(filename, "wb") as f:
        f.write(orjson.dumps(serialized_raw_data))


def load_raw_data(filename: str) -> dict[str, list[RawData]]:
    """Loads raw data from a file."""
    with open(filename, "rb") as f:
        serialized_raw_data = orjson.loads(f.read())

    loaded_raw_data: dict[str, list[RawData]] = defaultdict(list)
    for class_label, raw_data_entries in serialized_raw_data.items():
        for raw_data_entry in raw_data_entries:
            loaded_raw_data[class_label].append(
                RawData(
                    fpjs_data=[
                        RawFpjsData(
                            req_headers=raw_fpjs_data["req_headers"],
                            req_body=raw_fpjs_data["req_body"],
                        )
                        for raw_fpjs_data in raw_data_entry["fpjs_data"]
                    ],
                    behavioral_data=[
                        RawMmData(
                            req_headers=raw_mm_data["req_headers"],
                            req_body=raw_mm_data["req_body"],
                        )
                        for raw_mm_data in raw_data_entry["behavioral_data"]
                    ],
                    source=DataSource.from_dict(raw_data_entry["source"]),
                )
            )

    return loaded_raw_data


@dataclass
class AgentClassificationDataset:
    data: dict[str, dict[str, dict[str, list[float]]]]
    label_mapping: dict[str, int]

    def __init__(
        self,
        data: dict[str, dict[str, dict[str, list[float]]]],
        label_mapping: dict[str, int] | None = None,
    ):
        self.data = data
        if label_mapping is None:
            self.label_mapping = self.create_label_mapping()
        else:
            self.label_mapping = label_mapping

    def create_label_mapping(self) -> dict[str, int]:
        self.label_mapping = {
            label: i for i, label in enumerate(sorted(list(self.data.keys())))
        }
        return self.label_mapping

    @staticmethod
    def from_json(json_str: bytes | str) -> "AgentClassificationDataset":
        """Loads dataset from a JSON string."""
        file_data = orjson.loads(json_str)
        return AgentClassificationDataset(file_data["data"], file_data["label_mapping"])

    def to_json(self) -> bytes:
        """Saves dataset to a JSON string."""
        return orjson.dumps({"data": self.data, "label_mapping": self.label_mapping})

    def get_X_y(self, labeled: bool = False) -> tuple[np.ndarray, np.ndarray]:
        """Returns a tuple of (X, y)."""
        X = []
        y = []
        for class_label, data in self.data.items():
            for source, fvs in data.items():
                X.append((source, fvs)) if labeled else X.append(fvs)
                y.append(self.label_mapping[class_label])
        return np.array(X), np.array(y)

    def get_split(
        self,
        validation_size: float = 0.0,
        test_size: float = 0.2,
        random_state: int = 32,
        labeled: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns a tuple of (X_train, X_val, X_test, y_train, y_val, y_test).
        If validation_size is 0, returns (X_train, X_test, y_train, y_test).
        """
        X, y = self.get_X_y(labeled=labeled)

        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        if validation_size > 0.0:
            X_train, X_val, y_train, y_val = train_test_split(
                X_temp,
                y_temp,
                test_size=validation_size / (1 - test_size),
                random_state=random_state,
                stratify=y_temp,
            )
            return (
                np.array(X_train),
                np.array(X_val),
                np.array(X_test),
                np.array(y_train),
                np.array(y_val),
                np.array(y_test),
            )
        else:
            return (
                np.array(X_temp),
                np.array([]),
                np.array(X_test),
                np.array(y_temp),
                np.array([]),
                np.array(y_test),
            )


class DataProcessor:
    def __init__(self):
        self.conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        # Map class label to list of RawData
        self.raw_data: dict[str, list[RawData]] = defaultdict(list)
        # Map class label to list of ProcessedData
        self.processed_data: dict[str, list[ProcessedData]] = defaultdict(list)

    def __del__(self):
        self.conn.close()

    def get_data(self, result_file: str, check_visitor_id: bool = False) -> None:
        """
        Gets data from database corresponding to experiments described in
        result file.
        """
        with open(result_file, "r") as f:
            experiments = orjson.loads(f.read())

        for website_version, test_details in experiments.items():
            ai_platform = test_details["ai_platform"]
            # If we want to be more specific with classes
            # interface = test_details["interface"]
            # llm_model = test_details["llm_model"]
            # browser_type = test_details["browser_type"]
            # headful = test_details["headful"]
            for task_name, trials in test_details["tasks"].items():
                for trial in trials:
                    start_time = trial["start_time"]
                    end_time = trial["end_time"]
                    source = DataSource(
                        website_version=website_version,
                        class_label=ai_platform,
                        task_name=task_name,
                        trial_index=trial["trial_num"],
                        start_time=start_time,
                        end_time=end_time,
                        source_file=result_file,
                    )
                    self._retrieve_data(
                        start_time, end_time, website_version, source, check_visitor_id
                    )

    def _parse_header_text(self, header_text: str) -> dict[str, str]:
        """Parses header text into a dictionary of headers."""
        header_lines = [line.split(": ") for line in header_text.strip().splitlines()]
        return {x[0]: x[1] for x in header_lines}

    def _process_raw_fpjs_data(
        self, data_object: ProcessedData, raw_data: RawData
    ) -> bool:
        for raw_fpjs_data in raw_data.fpjs_data:
            headers = self._parse_header_text(raw_fpjs_data.req_headers)
            if headers.get("X-Source") == "result":
                fpjs_obj = FingerprintFV()
                fpjs_obj.parse_traffic_data(
                    headers, orjson.loads(raw_fpjs_data.req_body)
                )
                data_object.fpjs_feature_vector = fpjs_obj
                return True
        return False

    def _process_raw_behavioral_data(
        self, data_object: ProcessedData, raw_data: RawData
    ) -> bool:
        events = []
        for raw_behavioral_data in raw_data.behavioral_data:
            req_body = orjson.loads(raw_behavioral_data.req_body)
            if "eventFrames" in req_body:
                # Convert lists to tuples and preprocess (in case of old data format)
                event_frames = [
                    preprocess_tuple(tuple(event)) for event in req_body["eventFrames"]
                ]
                events.extend(event_frames)

        behavioral_feature_vector = BehavioralFV()
        behavioral_feature_vector.parse_events(events)
        data_object.behavioral_feature_vector = behavioral_feature_vector
        return True

    def process_data(self) -> None:
        """Processes raw data into feature vectors with source tracking."""
        for class_label, raw_data_list in self.raw_data.items():
            for raw_data in raw_data_list:
                data_obj = ProcessedData(
                    fpjs_feature_vector=None,
                    behavioral_feature_vector=None,
                    source=raw_data.source,
                )
                self._process_raw_fpjs_data(data_obj, raw_data)
                self._process_raw_behavioral_data(data_obj, raw_data)
                self.processed_data[class_label].append(data_obj)

    def load_raw_data(self, filename: str) -> None:
        with open(filename, "rb") as f:
            serialized_raw_data = orjson.loads(f.read())

        loaded_raw_data: dict[str, list[RawData]] = defaultdict(list)
        for class_label, raw_data_entries in serialized_raw_data.items():
            for raw_data_entry in raw_data_entries:
                loaded_raw_data[class_label].append(
                    RawData(
                        fpjs_data=[
                            RawFpjsData(
                                req_headers=raw_fpjs_data["req_headers"],
                                req_body=raw_fpjs_data["req_body"],
                            )
                            for raw_fpjs_data in raw_data_entry["fpjs_data"]
                        ],
                        behavioral_data=[
                            RawMmData(
                                req_headers=raw_mm_data["req_headers"],
                                req_body=raw_mm_data["req_body"],
                            )
                            for raw_mm_data in raw_data_entry["behavioral_data"]
                        ],
                        source=DataSource.from_dict(raw_data_entry["source"]),
                    )
                )

        self.raw_data = loaded_raw_data

    def save_raw_data(self, filename: str) -> None:
        serialized_raw_data: dict[str, list[dict[str, Any]]] = {}
        for class_label, raw_data_entries in self.raw_data.items():
            serialized_raw_data[class_label] = []
            for raw_data_entry in raw_data_entries:
                serialized_raw_data[class_label].append(
                    {
                        "fpjs_data": [
                            {
                                "req_headers": raw_fpjs_data.req_headers,
                                "req_body": raw_fpjs_data.req_body,
                            }
                            for raw_fpjs_data in raw_data_entry.fpjs_data
                        ],
                        "behavioral_data": [
                            {
                                "req_headers": raw_mm_data.req_headers,
                                "req_body": raw_mm_data.req_body,
                            }
                            for raw_mm_data in raw_data_entry.behavioral_data
                        ],
                        "source": raw_data_entry.source.to_dict(),
                    }
                )

        with open(filename, "wb") as f:
            f.write(orjson.dumps(serialized_raw_data))

    def _retrieve_data(
        self,
        start_time: str,
        end_time: str,
        website_version: str,
        source: DataSource,
        check_visitor_id: bool = False,
    ) -> None:
        """Retrieves raw data from database for both fpjs and mm endpoints."""
        raw_data = RawData(
            fpjs_data=[],
            behavioral_data=[],
            source=source,
        )

        if check_visitor_id:
            visitor_id = source.task_name.split()[1]

        # Retrieve fpjs data
        fpjs_query = (
            f"SELECT req_headers, req_body FROM requests "
            + f"WHERE website_version = '{website_version}' "
            + f"AND req_ts BETWEEN '{start_time}' AND '{end_time}' "
            + f"AND endpoint = '/{website_version}/fp' "
            + (
                f"AND req_body <> '' and  (req_body::jsonb)->'result'->>'visitorId' = '{visitor_id}' "
                if check_visitor_id
                else ""
            )
            + f"ORDER BY req_ts ASC"
        )
        with self.conn.cursor() as cursor:
            cursor.execute(fpjs_query)
            fpjs_rows = cursor.fetchall()
            for req_headers, req_body in fpjs_rows:
                raw_data.fpjs_data.append(
                    RawFpjsData(
                        req_headers=req_headers,
                        req_body=req_body,
                    )
                )

        # Retrieve behavioral data
        mm_query = (
            f"SELECT req_headers, req_body FROM requests "
            + f"WHERE website_version = '{website_version}' "
            + f"AND req_ts BETWEEN '{start_time}' AND '{end_time}' "
            + f"AND endpoint = '/{website_version}/mm' "
            + (
                f"AND req_body <> '' and (req_body::jsonb)->>'visitorId' = '{visitor_id}' "
                if check_visitor_id
                else ""
            )
            + f"ORDER BY req_ts ASC"
        )

        with self.conn.cursor() as cursor:
            cursor.execute(mm_query)
            mm_rows = cursor.fetchall()
            for req_headers, req_body in mm_rows:
                raw_data.behavioral_data.append(
                    RawMmData(
                        req_headers=req_headers,
                        req_body=req_body,
                    )
                )

        self.raw_data[source.class_label].append(raw_data)

    def get_dataset(self) -> dict[str, dict[DataSource, dict[str, list[float]]]]:
        """
        Returns a dictionary mapping class labels to a dictionary mapping
        DataSource to a dictionary containing the fpjs and behavioral feature
        vectors.
        """
        dataset: dict[str, dict[DataSource, dict[str, list[float]]]] = {}
        for class_label, processed_data_list in self.processed_data.items():
            dataset[class_label] = defaultdict(dict)
            for processed_data in processed_data_list:
                try:
                    dataset[class_label][processed_data.source] = {
                        "fpjs": processed_data.fpjs_feature_vector.extract_feature_vector(),
                        "behavioral": processed_data.behavioral_feature_vector.extract_feature_vector(),
                    }
                except Exception as e:
                    print(f"Error processing data for {processed_data.source}: {e}")
                    traceback.print_exc()
        return dataset

    def to_dict(self) -> dict[str, dict[str, dict[str, list[float]]]]:
        dataset = self.get_dataset()
        json_ready_dataset = {}
        for class_label, data in dataset.items():
            json_ready_dataset[class_label] = {}
            for source, fvs in data.items():
                json_ready_dataset[class_label][
                    orjson.dumps(source.to_dict()).decode("utf-8")
                ] = {
                    "fpjs": fvs["fpjs"],
                    "behavioral": fvs["behavioral"],
                }
        return json_ready_dataset

    def save_dataset(self, output_file: str) -> None:
        """Saves dataset to a file."""
        json_ready_dataset = self.to_dict()
        with open(output_file, "wb") as f:
            f.write(orjson.dumps(json_ready_dataset))

    @staticmethod
    def from_dict(
        dataset: dict[str, dict[str, dict[str, list[float]]]],
    ) -> "DataProcessor":
        """
        Loads dataset from a dictionary.

        The dictionary structure should match what to_dict() produces:
        dict[str, dict[str, dict[str, list[float]]]]
        where the middle dict has string keys (JSON-encoded DataSource objects).
        """
        data_processor = DataProcessor()
        for class_label, data in dataset.items():
            for source_str, fvs in data.items():
                data_processor.processed_data[class_label].append(
                    ProcessedData(
                        fpjs_feature_vector=FingerprintFV(fvs["fpjs"]),
                        behavioral_feature_vector=BehavioralFV(fvs["behavioral"]),
                        source=DataSource.from_dict(orjson.loads(source_str)),
                    )
                )
        return data_processor

    @staticmethod
    def load_dataset(input_file: str) -> "DataProcessor":
        """Loads dataset from a file."""
        with open(input_file, "rb") as f:
            dataset = orjson.loads(f.read())
        return DataProcessor.from_dict(dataset)
