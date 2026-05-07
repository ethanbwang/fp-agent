import os

import numpy as np
import xgboost as xgb

from classifier_training.types import FeatureType
from classifier_training.data_processing import (
    DataProcessor,
    AgentClassificationDataset,
)


def remove_iqr_outliers(values: list[float]) -> list[float]:
    if len(values) < 4:
        return values

    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    return [v for v in values if lower_bound <= v <= upper_bound]


def get_dataset(
    result_files: list[str],
    output_file: str,
    raw_data_file: str | None = None,
    overwrite_raw_cache: bool = False,
    check_visitor_id: bool = False,
) -> AgentClassificationDataset:
    """
    Create dataset from the list of files in `datafiles` and save to `output_file`. Returns the dataset.
    """
    data_processor = DataProcessor()
    abs_raw_data_path = (
        os.path.join(os.getcwd(), raw_data_file) if raw_data_file is not None else None
    )
    if (
        abs_raw_data_path is not None
        and not overwrite_raw_cache
        and os.path.exists(abs_raw_data_path)
    ):
        data_processor.load_raw_data(abs_raw_data_path)
    else:
        for result_file in result_files:
            data_processor.get_data(result_file, check_visitor_id)

    data_processor.process_data()

    if not os.path.exists(abs_raw_data_path) or overwrite_raw_cache:
        data_processor.save_raw_data(abs_raw_data_path)

    # Save fpjs and behavioral feature vectors and their source to a file, grouped by class label (agent name)
    data_processor.save_dataset(output_file)

    # Process raw dataset into AgentClassificationDataset
    dataset = data_processor.to_dict()

    return AgentClassificationDataset(dataset)


def load_dataset(
    dataset_file: str, removed_classes: list[str] = []
) -> AgentClassificationDataset:
    combined_dataset = DataProcessor.load_dataset(dataset_file)
    dataset = combined_dataset.to_dict()
    if removed_classes:
        dataset = {k: dataset[k] for k in dataset if k not in removed_classes}
    dataset = AgentClassificationDataset(data=dataset)
    return dataset


def get_dataset_split(
    dataset: AgentClassificationDataset,
    validation_size: float = 0.0,
    test_size: float = 0.2,
    random_state: int = 32,
):
    return dataset.get_split(
        validation_size=validation_size,
        test_size=test_size,
        random_state=random_state,
    )


def save_dataset_split(
    X_train, X_val, X_test, y_train, y_val, y_test, output_file: str
) -> None:
    np.savez(
        file=output_file,
        X_train=X_train,
        X_val=X_val,
        X_test=X_test,
        y_train=y_train,
        y_val=y_val,
        y_test=y_test,
    )


def load_dataset_split(
    input_file: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    data = np.load(input_file, allow_pickle=True)
    return (
        data["X_train"],
        data["X_val"],
        data["X_test"],
        data["y_train"],
        data["y_val"],
        data["y_test"],
    )


def get_feature_vectors(
    X_train, X_val, X_test, feature_type: FeatureType
) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None]:
    """
    Returns (train, val, test) feature vectors for the given feature type.
    Extracted from dictionary containing "fpjs" and "behavioral" keys.
    """
    if feature_type == FeatureType.BROWSER:
        return (
            np.array([x["fpjs"] for x in X_train]) if X_train is not None else None,
            np.array([x["fpjs"] for x in X_val]) if X_val is not None else None,
            np.array([x["fpjs"] for x in X_test]) if X_test is not None else None,
        )
    elif feature_type == FeatureType.BEHAVIORAL:
        return (
            (
                np.array([x["behavioral"] for x in X_train])
                if X_train is not None
                else None
            ),
            np.array([x["behavioral"] for x in X_val]) if X_val is not None else None,
            (
                np.array([x["behavioral"] for x in X_test])
                if X_test is not None
                else None
            ),
        )
    elif feature_type == FeatureType.COMBINED:
        return (
            (
                np.array([x["fpjs"] + x["behavioral"] for x in X_train])
                if X_train is not None
                else None
            ),
            (
                np.array([x["fpjs"] + x["behavioral"] for x in X_val])
                if X_val is not None
                else None
            ),
            (
                np.array([x["fpjs"] + x["behavioral"] for x in X_test])
                if X_test is not None
                else None
            ),
        )


def load_model(model_file: str) -> xgb.XGBClassifier:
    model = xgb.XGBClassifier(importance_type="total_gain")
    model.load_model(model_file)
    return model


def summary_stats_1d(values):
    """Compute summary stats for a 1D list of numeric values (skips non-numeric/None)."""
    numeric = []
    for v in values:
        try:
            numeric.append(float(v))
        except (TypeError, ValueError):
            continue

    if len(numeric) == 0:
        return {
            "n": 0,
            "mean": None,
            "std": None,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "max": None,
        }

    arr = np.asarray(numeric, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {
            "n": 0,
            "mean": None,
            "std": None,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "max": None,
        }

    p25, median, p75 = np.percentile(arr, [25, 50, 75])
    std = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0

    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "std": std,
        "min": float(np.min(arr)),
        "p25": float(p25),
        "median": float(median),
        "p75": float(p75),
        "max": float(np.max(arr)),
    }
