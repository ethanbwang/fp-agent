"""
Run holdout experiments for a given dataset, split file, feature type, and removed classes.

Usage:
uv run scripts/holdout_task_experiment.py --dataset_file <dataset_file>
--split_file <split_file> --feature_type <feature_type> --removed_classes <removed_classes>
"""

import argparse
from dataclasses import dataclass
import os

from classifier_training.classifier import TrainingPipeline
from classifier_training.types import FeatureType


@dataclass
class TaskSplit:
    train_tasks: tuple[str, str]
    test_task: str


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset_file", type=str, required=True, help="Path to dataset file"
    )
    parser.add_argument(
        "--split_file", type=str, required=True, help="Path to split file"
    )
    parser.add_argument(
        "--feature_type",
        type=str,
        default="BEHAVIORAL",
        help="Feature type to use, defaults to BEHAVIORAL",
    )
    parser.add_argument(
        "--removed_classes",
        type=list,
        default=[],
        help="List of classes to remove from class set",
    )
    parser.add_argument(
        "--output_dir", type=str, help="Directory to save models, defaults to /tmp"
    )
    args = parser.parse_args()

    if args.output_dir is None:
        output_dir = "/tmp"
    else:
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)

    feature_type = FeatureType[args.feature_type.upper()]

    pipeline = TrainingPipeline(
        dataset_file=args.dataset_file,
        split_file=args.split_file,
        feature_type=feature_type,
        removed_classes=args.removed_classes,
    )

    split_data = pipeline.group_data_by_task()

    task_splits = [
        TaskSplit(("Shopping", "Flight-booking"), "Forums"),
        TaskSplit(("Shopping", "Forums"), "Flight-booking"),
        TaskSplit(("Flight-booking", "Forums"), "Shopping"),
    ]

    for task_split in task_splits:
        train_tasks, test_task = task_split.train_tasks, task_split.test_task

        # Get train and test sets
        X_train = []
        y_train = []
        X_test = []
        y_test = []
        for agent, data in split_data.items():
            # Train set
            for task in train_tasks:
                if feature_type == FeatureType.BROWSER:
                    X_train += [x["fpjs"] for x in data[task]]
                elif feature_type == FeatureType.BEHAVIORAL:
                    X_train += [x["behavioral"] for x in data[task]]
                else:
                    X_train += [x["fpjs"] + x["behavioral"] for x in data[task]]

                y_train += [
                    pipeline.dataset.label_mapping[agent]
                    for _ in range(len(data[task]))
                ]

            # Test set
            if feature_type == FeatureType.BROWSER:
                X_test += [x["fpjs"] for x in data[test_task]]
            elif feature_type == FeatureType.BEHAVIORAL:
                X_test += [x["behavioral"] for x in data[test_task]]
            else:
                X_test += [x["fpjs"] + x["behavioral"] for x in data[test_task]]

            y_test += [
                pipeline.dataset.label_mapping[agent]
                for _ in range(len(data[test_task]))
            ]

        train_pipeline = TrainingPipeline(
            dataset_file=args.dataset_file,
            split_file=args.split_file,
            feature_type=feature_type,
            removed_classes=args.removed_classes,
        )

        train_pipeline.X_train_vectors = X_train
        train_pipeline.X_test_vectors = X_test
        train_pipeline.y_train = y_train
        train_pipeline.y_test = y_test

        train_pipeline.train_model(
            model_file=f"{output_dir}/{feature_type.value}_one_task_out_model_{train_tasks}_{test_task}.json",
        )
        print(train_tasks, test_task)
        print(train_pipeline.evaluate_model())


if __name__ == "__main__":
    main()
