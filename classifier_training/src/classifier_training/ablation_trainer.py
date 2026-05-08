"""
Train XGBClassifier with iterative feature removal by importance.

For each iteration: train classifier; evaluate F1; if F1 >= threshold, save model;
remove top-importance feature. Stops when F1 drops below threshold or no
features remain. Saved model filenames encode step index and removed features.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from dotenv import load_dotenv
import json
import os
import shutil
import yaml

load_dotenv()
PROJECT_ROOT = os.getenv("PROJECT_ROOT")

from classifier_training.feature_index import get_feature_index, get_feature_name
from classifier_training.types import FeatureType
from classifier_training.classifier import TrainingPipeline


"""
1. Create working directory if it doesn't exist
2. Copy config to working directory
3. Load dataset from dataset_path
4. Load dataset split from split_path
5. Run ablation
  a. Create step directory
  b. Train initial model
  c. Run calculations of metrics, feature importance, and SHAP
  d. Save calculations and model to step directory
  e. Repeat steps a-d until F1 drops to chance level or max_steps is reached
    i. Chance level is defined as 1 / number of classes
"""


@dataclass
class AblationConfig:
    config_path: str
    work_dir: str
    dataset_path: str
    split_path: str

    # Used to get correct feature vectors
    feature_type: FeatureType
    removed_classes: list[str]

    # Parameters for training
    test_size: float = 0.2
    validation_size: float = 0.0
    max_depth: int = 6
    n_estimators: int = 150
    learning_rate: float = 0.1
    random_state: int = 32
    max_steps: int | None = None

    def __init__(self, config_path: str):
        self.config_path = config_path
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        self.work_dir = (
            f"{PROJECT_ROOT}/{config["work_dir"]}"
            if PROJECT_ROOT is not None
            else config["work_dir"]
        )
        self.dataset_path = (
            f"{PROJECT_ROOT}/{config["dataset_file"]}"
            if PROJECT_ROOT is not None
            else config["dataset_file"]
        )
        self.split_path = (
            f"{PROJECT_ROOT}/{config["split_file"]}"
            if PROJECT_ROOT is not None
            else config["split_file"]
        )
        self.feature_type = FeatureType[config["feature_type"].upper()]
        self.removed_classes = config["removed_classes"]
        self.test_size = config["test_size"]
        self.validation_size = config["validation_size"]
        self.max_depth = config["max_depth"]
        self.n_estimators = config["n_estimators"]
        self.learning_rate = config["learning_rate"]
        self.random_state = config["random_state"]
        self.max_steps = config["max_steps"]


class Ablation:
    def __init__(self, config_path: str):
        self.config = AblationConfig(config_path)

    def run_ablation(self) -> None:
        """
        Train XGBClassifier, then repeatedly remove the top-importance feature and
        retrain until test F1 drops below chance level or no more features are important.
        """

        # Setup directories
        work_dir = os.path.join(PROJECT_ROOT, self.config.work_dir)
        os.makedirs(work_dir, exist_ok=True)
        log_path = os.path.join(work_dir, "log.txt")

        # Config can be used to identify the ablation run.
        # Copy the config to the working directory.
        shutil.copy(self.config.config_path, work_dir)

        training_pipeline = TrainingPipeline(
            dataset_file=self.config.dataset_path,
            split_file=self.config.split_path,
            feature_type=self.config.feature_type,
            removed_classes=self.config.removed_classes,
        )

        step = 0
        # Indices are from initial feature vector
        removed_indices = []
        max_steps = (
            self.config.max_steps if self.config.max_steps is not None else float("inf")
        )

        while step < max_steps:
            step_dir = os.path.join(work_dir, f"step{step}")
            os.makedirs(step_dir, exist_ok=True)

            # Train classifier
            training_pipeline.get_X_vectors(removed_indices)
            if len(training_pipeline.X_train_vectors[0]) == 0:
                print(f"Step {step}: No remaining features. Stopping.")
                break

            training_pipeline.train_model(
                model_file=os.path.join(step_dir, f"step{step}_classifier.json"),
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                n_estimators=self.config.n_estimators,
                random_state=self.config.random_state,
            )

            # Calculate metrics, feature importance, and SHAP
            metrics = training_pipeline.evaluate_model()
            training_pipeline.calculate_shap_values(self.config.feature_type)
            ranked_importance = training_pipeline.get_feature_importance_ranking()
            per_class_shap = training_pipeline.get_per_class_shap()

            # Save metrics, feature importance, and SHAP to step directory
            with open(os.path.join(step_dir, f"step{step}_metrics.json"), "w") as f:
                json.dump(metrics, f, indent=2)
            with open(
                os.path.join(step_dir, f"step{step}_feature_importance.json"), "w"
            ) as f:
                json.dump(ranked_importance, f, indent=2)
            with open(
                os.path.join(step_dir, f"step{step}_per_class_shap.json"), "w"
            ) as f:
                json.dump(per_class_shap, f, indent=2)

            if step == 0:
                training_pipeline.save_shap_matrix(
                    os.path.join(step_dir, f"step{step}_shap_matrix")
                )

            # Save step metadata including which features have been removed
            meta = {
                "step": step,
                "removed_indices": removed_indices,
                "removed_feature_names": get_feature_name(
                    self.config.feature_type, removed_indices
                ),
            }
            with open(os.path.join(step_dir, f"step{step}_meta.json"), "w") as f:
                json.dump(meta, f, indent=2)

            # Stopping condition: no remaining features with nonzero importance
            nonzero_features = [
                entry for entry in ranked_importance if entry["importance"] > 0
            ]
            if not nonzero_features:
                print(
                    f"Step {step}: No remaining features with nonzero importance. Stopping."
                )
                break

            # Stopping condition: all per-class F1 scores at or below chance
            num_classes = len([k for k in metrics if k != "overall"])
            chance = 1.0 / num_classes
            all_at_chance = all(
                metrics[class_name]["f1"] <= chance
                for class_name in metrics
                if class_name != "overall"
            )
            if all_at_chance:
                print(f"Step {step}: All classes at chance level. Stopping.")
                break

            # Stopping condition: any class has F1 score of 0
            any_zero = any(
                metrics[class_name]["f1"] == 0
                for class_name in metrics
                if class_name != "overall"
            )
            if any_zero:
                print(f"Step {step}: At least one class has F1 score of 0. Stopping.")
                break

            # Select next feature to remove: find the first entry whose global index is not already removed
            global_feature_indices = get_feature_index(
                self.config.feature_type,
                [entry["feature"] for entry in ranked_importance],
            )

            next_feature = next(
                entry
                for entry in ranked_importance
                if global_feature_indices[entry["feature"]] not in removed_indices
                and entry["importance"] > 0
            )
            with open(log_path, "a", encoding="utf-8") as log_f:
                log_f.write(
                    f"Step {step}: Removing feature '{next_feature['feature']}' "
                    f"(local index {get_feature_index(self.config.feature_type, next_feature['feature'], removed_indices)[next_feature['feature']]}, global index {global_feature_indices[next_feature['feature']]}, importance {next_feature['importance']:.4f})"
                    f"F1 score: {metrics['overall']['f1']:.4f}\n"
                )
            removed_indices.append(global_feature_indices[next_feature["feature"]])

            step += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_path", type=str, required=True)
    args = parser.parse_args()
    ablation = Ablation(args.config_path)
    ablation.run_ablation()
    print("Ablation complete.")
