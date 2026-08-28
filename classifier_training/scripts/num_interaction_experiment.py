"""
Run num interaction experiments for a given raw dataset, feature type, event type,
k start, and k end.

Usage:
uv run scripts/num_interaction_experiment.py --raw_data_file <raw_data_file>
--k_start <k_start> --k_end <k_end> --out_file <out_file> --event_type <event_type>
"""

import argparse
import json
import os
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import xgboost as xgb


from classifier_training.data_processing import (
    RawData,
    DataProcessor,
)
from classifier_training.data_preprocessing import preprocess_tuple
from classifier_training.featurizer import BehavioralFV, FingerprintFV
from classifier_training.types import EventType, FeatureType


# UI element IDs that are changed by mouse interactions
MOUSE_CHANGE_ELEMENTS = {
    "#price-select",
    "#category-select",
    "#sort-select",
    "#flight-date",
    "#carryOn",
    "#seatNumber",
    "#seatLetter",
    "#ticketType",
    "html > body:nth-child(2) > main:nth-child(2) > div:nth-child(3) > form:nth-child(3) > fieldset:nth-child(4) > label:nth-child(4) > input:nth-child(1)",
    "html > body:nth-child(2) > main:nth-child(2) > div:nth-child(3) > form:nth-child(3) > fieldset:nth-child(4) > label:nth-child(3) > input:nth-child(1)",
    "html > body:nth-child(2) > main:nth-child(2) > div:nth-child(3) > form:nth-child(3) > fieldset:nth-child(4) > label:nth-child(2) > input:nth-child(1)",
}

EVENT_TYPE_MAP = {
    "mm": EventType.MOUSE,
    "md": EventType.MOUSE,
    "mu": EventType.MOUSE,
    "ku": EventType.KEYBOARD,
    "kd": EventType.KEYBOARD,
    "sc": EventType.SCROLL,
    "se": EventType.SCROLL,
    "i": EventType.KEYBOARD,
    "p": EventType.KEYBOARD,
}

CLASS_MAPPING = {
    "Atlas Agent": 0,
    "Browser Use": 1,
    "ChatGPT Agent": 2,
    "Claude": 3,
    "Comet": 4,
    "Manus": 5,
    "Skyvern": 6,
    "Human": 7,
}

TASK_SET = {"ALL", "FLIGHT-BOOKING", "SHOPPING", "FORUMS"}


def get_change_event_type(event: list) -> Literal[EventType.KEYBOARD, EventType.MOUSE]:
    assert event[0] == "c", "`event` is not a change event"
    return EventType.MOUSE if event[1] in MOUSE_CHANGE_ELEMENTS else EventType.KEYBOARD


def parse_header_text(header_text: str) -> dict[str, str]:
    """Parses header text into a dictionary of headers."""
    header_lines = [line.split(": ") for line in header_text.strip().splitlines()]
    return {x[0]: x[1] for x in header_lines}


def process_raw_fpjs_data(raw_data: RawData) -> list[float]:
    for raw_fpjs_data in raw_data.fpjs_data:
        headers = parse_header_text(raw_fpjs_data.req_headers)
        if headers.get("X-Source") == "result":
            fpjs_obj = FingerprintFV()
            fpjs_obj.parse_traffic_data(headers, json.loads(raw_fpjs_data.req_body))
            return fpjs_obj.extract_feature_vector()
    raise ValueError("No FPJS request found in raw data")


def process_raw_behavioral_data(events: list[list[Any]]) -> list[float]:
    events = [preprocess_tuple(tuple(event)) for event in events]
    behavioral_feature_vector = BehavioralFV()
    behavioral_feature_vector.parse_events(events)
    return behavioral_feature_vector.extract_feature_vector()


def get_k_events_from_raw_data(
    raw_data: RawData,
    event_type: EventType,
    k: int,
) -> list[list[Any]]:
    """
    Returns a list of events of type `event_type` from the raw data.
    If k < 0, it will return all events.
    If k >= 0, it will return the first k events.
    """
    # Compare k to 0:
    # If k = -1, it will always process all events since k will always be less than 0
    # If k >= 0, it will process k events
    events = []
    for raw_mm_data in raw_data.behavioral_data:
        # This `if` statement is used to break the outer loop when k is 0
        if k == 0:
            break
        for event in json.loads(raw_mm_data.req_body)["eventFrames"]:
            if k == 0:
                break

            cur_event_type = (
                get_change_event_type(event)
                if event[0] == "c"
                else EVENT_TYPE_MAP[event[0]]
            )
            if event_type == EventType.ALL or cur_event_type == event_type:
                events.append(event)
                k -= 1
    return events


def get_X_fvs_from_raw_data(
    X_data: list[RawData],
    feature_type: FeatureType = FeatureType.BEHAVIORAL,
    event_type: EventType = EventType.ALL,
    k: int = -1,
) -> np.ndarray:
    X_fvs: list[list[float]] = []
    for raw_data in X_data:
        # Get browser fingerprint feature vector
        if feature_type != FeatureType.BEHAVIORAL:
            fpjs_fv = process_raw_fpjs_data(raw_data)
        else:
            fpjs_fv = []

        # Get behavioral feature vector
        if feature_type != FeatureType.BROWSER:
            # Get events from raw data
            events_to_process = get_k_events_from_raw_data(raw_data, event_type, k)

            # Process events_to_process into feature vector
            behavioral_fv = process_raw_behavioral_data(events_to_process)
        else:
            behavioral_fv = []

        X_fvs.append(fpjs_fv + behavioral_fv)
    return np.array(X_fvs)


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    model_file: str | None = None,
    max_depth: int = 6,
    learning_rate: float = 0.1,
    n_estimators: int = 150,
    random_state: int = 32,
) -> xgb.XGBClassifier:
    xgb_classifier = xgb.XGBClassifier(
        objective="multi:softmax",
        num_class=len(np.unique(y_train)),
        max_depth=max_depth,
        learning_rate=learning_rate,
        n_estimators=n_estimators,
        random_state=random_state,
        importance_type="total_gain",
    )

    xgb_classifier.fit(X_train, y_train)
    if model_file is not None:
        os.makedirs(os.path.dirname(model_file), exist_ok=True)
        xgb_classifier.save_model(model_file)
    return xgb_classifier


def evaluate_model(
    model: xgb.XGBClassifier, X_test: np.ndarray, y_test: np.ndarray
) -> dict[str, dict[str, float]]:
    """
    Returns a dictionary with the overall metrics and per-class metrics.
    The keys are "overall" and the class names.
    The values are dictionaries with the metrics.
    """
    y_pred = model.predict(X_test)

    # Overall metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision_macro = precision_score(y_test, y_pred, average="macro", zero_division=0)
    recall_macro = recall_score(y_test, y_pred, average="macro", zero_division=0)
    f1_macro = f1_score(y_test, y_pred, average="macro", zero_division=0)

    # Per-class metrics (array indexed by class integer)
    precision_per_class = precision_score(y_test, y_pred, average=None, zero_division=0)
    recall_per_class = recall_score(y_test, y_pred, average=None, zero_division=0)
    f1_per_class = f1_score(y_test, y_pred, average=None, zero_division=0)

    # Map class integers back to class names
    # class_names = list(np.unique(y_test))
    class_names = list(CLASS_MAPPING.keys())
    per_class = {
        class_names[i]: {
            "precision": float(precision_per_class[i]),
            "recall": float(recall_per_class[i]),
            "f1": float(f1_per_class[i]),
        }
        for i in range(len(class_names))
    }

    return {
        "overall": {
            "accuracy": accuracy,
            "precision": precision_macro,
            "recall": recall_macro,
            "f1": f1_macro,
        },
        **per_class,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_data_file", type=str)
    parser.add_argument("--feature_type", type=str, default="BEHAVIORAL")
    parser.add_argument("--event_type", type=str, default="ALL")
    parser.add_argument("--k_start", type=int, default=-1)
    parser.add_argument("--k_end", type=int, default=-1)
    parser.add_argument("--save_model", type=str, default="")
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--random_state", type=int, default=32)
    parser.add_argument("--task_set", type=str, default="ALL")
    parser.add_argument("--out_file", type=str, default="")
    args = parser.parse_args()

    feature_type = FeatureType[args.feature_type.upper()]
    event_type = EventType[args.event_type.upper()]
    task_set = args.task_set.upper()

    data_processor = DataProcessor()
    data_processor.load_raw_data(args.raw_data_file)

    X: list[RawData] = []
    y: list[int] = []
    for class_label, raw_data_list in data_processor.raw_data.items():
        for raw_data in raw_data_list:
            if task_set == "ALL" or task_set in raw_data.source.task_name.upper():
                X.append(raw_data)
                y.append(CLASS_MAPPING[class_label])

    # Do new data split on raw data, keep the split in memory
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=y,
    )

    # Process X_train
    X_train = get_X_fvs_from_raw_data(
        X_train, feature_type=feature_type, event_type=EventType.ALL, k=-1
    )

    # Train behavioral classifier on X_train, test with X_test
    if args.save_model == "":
        args.save_model = "/tmp/num_interaction_experiment_model.json"
    model = train_model(
        X_train, y_train, model_file=args.save_model, random_state=args.random_state
    )

    k_start = args.k_start
    k_end = args.k_end
    if k_start == -1:
        k_start = k_end
    if k_end == -1:
        k_end = k_start

    rows = []
    for k in tqdm(
        range(k_start, k_end + 1),
        desc=f"Running num interaction experiment with feature type={feature_type} and event type={event_type} from k={k_start} to k={k_end}",
    ):
        # Process X_test
        # For each datapoint in X_test, compute fv with just k events of event type
        X_test_at_k = get_X_fvs_from_raw_data(
            X_test, feature_type=feature_type, event_type=event_type, k=k
        )

        # Test behavioral classifier and print metrics
        # logger.info(f"k: {k}, metrics: {evaluate_model(model, X_test_at_k, y_test)}")
        metrics = evaluate_model(model, X_test_at_k, y_test)
        rows.append(
            {
                "Feature Type": feature_type.name,
                "Event Type": event_type.name,
                "k": k,
                "Accuracy": metrics["overall"]["accuracy"],
                "Precision": metrics["overall"]["precision"],
                "Recall": metrics["overall"]["recall"],
                "F1": metrics["overall"]["f1"],
            }
        )

    df = pd.DataFrame(rows)
    if args.out_file != "":
        df.to_csv(args.out_file, index=False)


if __name__ == "__main__":
    main()
