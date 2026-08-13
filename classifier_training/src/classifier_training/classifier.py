from collections import defaultdict
import os
import json

from dotenv import load_dotenv

load_dotenv()

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# import scienceplots
import shap
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
from sklearn.model_selection import train_test_split
import xgboost as xgb

from classifier_training.types import FeatureType
from classifier_training.common import (
    load_dataset,
    load_dataset_split,
    load_model,
    get_feature_vectors,
    remove_iqr_outliers,
    summary_stats_1d,
)
from classifier_training.feature_index import get_feature_name, get_feature_index


class TrainingPipeline:
    def __init__(
        self,
        dataset_file: str,
        split_file: str,
        feature_type: FeatureType,
        removed_classes: list[str] = [],
    ):
        self.dataset_file = dataset_file
        self.split_file = split_file
        self.removed_classes = removed_classes
        self.dataset = load_dataset(dataset_file, removed_classes)
        self.X_train, self.X_val, self.X_test, self.y_train, self.y_val, self.y_test = (
            load_dataset_split(split_file)
        )
        self.feature_type = feature_type

        self.removed_indices: list[int] = []
        self.X_train_vectors = None
        self.X_val_vectors = None
        self.X_test_vectors = None
        self.model: xgb.XGBClassifier | None = None

        self.y_pred = None
        self.shap_values = None
        self.shap_inter = None
        self.interaction_importance = None

    def print_dataset_class_counts(self) -> None:
        class_counts = defaultdict(int)
        for class_label in self.dataset.data:
            print(f"{class_label}: {len(self.dataset.data[class_label])}")
            class_counts[class_label] += len(self.dataset.data[class_label])
            for _, fvs in self.dataset.data[class_label].items():
                if fvs["behavioral"] is None or fvs["behavioral"] == []:
                    print(fvs["fpjs"])
                    print(fvs["behavioral"])
        print(class_counts)

    def group_data_by_task(
        self,
    ) -> dict[str, dict[str, list[dict[str, list[float]]]]]:
        grouped_data = {}
        for class_label in self.dataset.data:
            grouped_data[class_label] = {}
            for source, fvs in self.dataset.data[class_label].items():
                source_dict = json.loads(source)
                task_name = source_dict["task_name"].split()[0]
                if task_name not in grouped_data[class_label]:
                    grouped_data[class_label][task_name] = []
                grouped_data[class_label][task_name].append(fvs)
        return grouped_data

    def get_X_vectors(self, removed_indices: list[int] = []) -> None:
        """
        Updates removed indices and feature vectors based on the removed indices.
        """
        self.removed_indices = removed_indices

        X_train_vectors, X_val_vectors, X_test_vectors = get_feature_vectors(
            self.X_train, self.X_val, self.X_test, self.feature_type
        )

        self.X_train_vectors = (
            np.delete(X_train_vectors, removed_indices, axis=1)
            if X_train_vectors is not None and len(X_train_vectors) > 0
            else None
        )
        self.X_val_vectors = (
            np.delete(X_val_vectors, removed_indices, axis=1)
            if X_val_vectors is not None and len(X_val_vectors) > 0
            else None
        )
        self.X_test_vectors = (
            np.delete(X_test_vectors, removed_indices, axis=1)
            if X_test_vectors is not None and len(X_test_vectors) > 0
            else None
        )

    def train_model(
        self,
        model_file: str,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        n_estimators: int = 150,
        random_state: int = 32,
    ) -> None:
        # Note: max_depth of 6 and n_estimators of 150 good enough.
        xgb_classifier = xgb.XGBClassifier(
            objective="multi:softmax",
            num_class=len(np.unique(self.dataset.label_mapping.keys())),
            max_depth=max_depth,
            learning_rate=learning_rate,
            n_estimators=n_estimators,
            random_state=random_state,
            importance_type="total_gain",
        )

        xgb_classifier.fit(self.X_train_vectors, self.y_train)
        os.makedirs(os.path.dirname(model_file), exist_ok=True)
        xgb_classifier.save_model(model_file)
        self.model = xgb_classifier

    def load_model(self, model_file: str) -> None:
        self.model = load_model(model_file)

    def evaluate_model(self) -> dict[str, dict[str, float]]:
        """
        Returns a dictionary with the overall metrics and per-class metrics.
        The keys are "overall" and the class names.
        The values are dictionaries with the metrics.
        """
        self.y_pred = self.model.predict(self.X_test_vectors)

        # Overall metrics
        accuracy = accuracy_score(self.y_test, self.y_pred)
        precision_macro = precision_score(
            self.y_test, self.y_pred, average="macro", zero_division=0
        )
        recall_macro = recall_score(
            self.y_test, self.y_pred, average="macro", zero_division=0
        )
        f1_macro = f1_score(self.y_test, self.y_pred, average="macro", zero_division=0)

        # Per-class metrics (array indexed by class integer)
        precision_per_class = precision_score(
            self.y_test, self.y_pred, average=None, zero_division=0
        )
        recall_per_class = recall_score(
            self.y_test, self.y_pred, average=None, zero_division=0
        )
        f1_per_class = f1_score(self.y_test, self.y_pred, average=None, zero_division=0)

        # Map class integers back to class names
        class_names = list(self.dataset.label_mapping.keys())
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

    def get_feature_importance_ranking(self) -> list[dict]:
        importance = self.model.feature_importances_  # total_gain, shape: (n_features,)
        feature_names = get_feature_name(
            self.feature_type, list(range(len(importance))), self.removed_indices
        )
        names = list(feature_names.values())

        ranked = sorted(
            zip(names, importance.tolist()), key=lambda x: x[1], reverse=True
        )

        return [{"feature": name, "importance": imp} for name, imp in ranked]

    def display_feature_importance(self, feature_type: FeatureType) -> plt.Figure:
        features = []
        for _, val in get_feature_name(
            feature_type,
            list(range(self.X_train_vectors.shape[1])),
            self.removed_indices,
        ).items():
            features.append(val.replace("_", " ").replace("mm", " mouse movement"))

        features = np.array(features)

        feature_importance = pd.Series(
            self.model.feature_importances_,
            index=features,
        )
        feature_importance = feature_importance[feature_importance != 0]
        feature_importance = feature_importance.sort_values(ascending=False)[:20]
        fig, ax = plt.subplots()
        feature_importance.plot.bar(ax=ax)
        ax.set_title(
            f"{feature_type.name.capitalize()} Feature Importance (Total Gain)"
        )
        ax.set_xlabel(f"{feature_type.name.capitalize()} Feature")
        ax.set_ylabel("Total Gain")
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha("right")
            label.set_rotation_mode("anchor")
        fig.tight_layout()
        return fig

    def display_confusion_matrix(self, ax: plt.Axes | None = None) -> plt.Figure:
        if self.y_pred is None:
            raise ValueError(
                "y_pred is not calculated. Please call self.evaluate_model() first."
            )

        label_mapping_keys = list(self.dataset.label_mapping.keys())
        y_test_names = [
            label_mapping_keys[self.y_test[i]] for i in range(len(self.y_test))
        ]
        y_pred_names = [
            label_mapping_keys[self.y_pred[i]] for i in range(len(self.y_pred))
        ]

        local_agents = []
        cloud_agents = []
        for label in label_mapping_keys:
            if label in ["ChatGPT Agent", "Manus"]:
                cloud_agents.append(label)
            elif label in ["Atlas Agent", "Browser Use", "Claude", "Comet", "Skyvern"]:
                local_agents.append(label)

        label_order = sorted(local_agents) + sorted(cloud_agents)
        if "Human" not in self.removed_classes:
            label_order.append("Human")

        cm = confusion_matrix(y_test_names, y_pred_names, labels=label_order)

        with plt.style.context(["science"]):
            if ax is None:
                _, ax = plt.subplots(figsize=(3.5, 3.0), dpi=300)

            disp = ConfusionMatrixDisplay(
                confusion_matrix=cm, display_labels=label_order
            )
            disp.plot(
                cmap=plt.cm.Blues, xticks_rotation="vertical", ax=ax, colorbar=False
            )
            ax.tick_params(
                which="both", top=False, right=False, bottom=False, left=False
            )
            ax.set_xlabel("Predicted")
            ax.set_ylabel("True")
            return ax

    def calculate_shap_values(self, feature_type: FeatureType) -> None:
        features = [
            f"{key}: {val}"
            for key, val in get_feature_name(
                feature_type,
                list(range(len(self.X_test_vectors[0]))),
                self.removed_indices,
            ).items()
        ]
        explainer = shap.TreeExplainer(self.model, feature_names=features)
        self.shap_values = explainer(self.X_test_vectors)

    def get_per_class_shap(self) -> dict[str, list[dict]]:
        if self.shap_values is None:
            raise ValueError("Call calculate_shap_values() first.")

        vals = self.shap_values.values  # (n_samples, n_features, n_classes)
        mean_abs_shap = np.abs(vals).mean(axis=0)  # (n_features, n_classes)

        feature_names = get_feature_name(
            self.feature_type, list(range(vals.shape[1])), self.removed_indices
        )
        names = list(feature_names.values())
        class_names = list(self.dataset.label_mapping.keys())

        # Filter to nonzero importance features only
        nonzero_mask = self.model.feature_importances_ > 0

        result = {}
        for class_idx, class_name in enumerate(class_names):
            class_shap = mean_abs_shap[:, class_idx]
            ranked = sorted(
                [
                    (name, float(shap_val))
                    for name, shap_val, nonzero in zip(names, class_shap, nonzero_mask)
                    if nonzero
                ],
                key=lambda x: x[1],
                reverse=True,
            )
            result[class_name] = [
                {"feature": name, "shap": shap_val} for name, shap_val in ranked
            ]

        return result

    def display_shap_values(self, class_index: int) -> plt.Figure:
        if self.shap_values is None:
            raise ValueError(
                "shap_values are not calculated. Please call self.calculate_shap_values() first."
            )
        shap.plots.beeswarm(self.shap_values[:, :, class_index], show=False)
        plt.title(
            f"SHAP values for class {list(self.dataset.label_mapping.keys())[class_index]}"
        )
        plt.tight_layout()
        return plt.gcf()

    def plot_multiclass_global_shap_bar(
        self,
        feature_type: FeatureType,
        top_n: int = 20,
        class_names: list[str] | None = None,
        feature_names: list[str] | None = None,
        colors: list[str] | None = None,
    ) -> plt.Figure:
        """
        Recreates the old multiclass SHAP summary bar plot:
        - y-axis: top_n features (by total mean |SHAP| across classes)
        - x-axis: mean |SHAP| (stacked by class)
        """
        if feature_names is None:
            feature_names = []
            for _, val in get_feature_name(
                feature_type,
                list(range(len(self.X_train_vectors[0]))),
                self.removed_indices,
            ).items():
                feature_names.append(
                    val.replace("_", " ").replace("mm", " mouse movement")
                )

            feature_names = np.array(feature_names)

        vals = self.shap_values.values  # (n_samples, n_features, n_classes)

        # mean(|SHAP|) over samples -> (n_features, n_classes)
        mean_abs = np.mean(np.abs(vals), axis=0)

        # total importance per feature (sum across classes) for sorting
        total_importance = mean_abs.sum(axis=1)

        # remove features with zero importance
        nonzero_mask = total_importance > 0
        mean_abs = mean_abs[nonzero_mask]
        feature_names = feature_names[nonzero_mask]
        total_importance = total_importance[nonzero_mask]

        # sort remaining features by total importance
        idx = np.argsort(total_importance)[::-1]

        # sort features by total importance (descending)
        idx = np.argsort(total_importance)[::-1]

        # keep only top_n
        idx = idx[:top_n]
        mean_abs_sorted = mean_abs[idx]
        feature_names_sorted = feature_names[idx]

        n_features, n_classes = mean_abs_sorted.shape

        if class_names is None:
            class_names = list(self.dataset.label_mapping.keys())
        # if class_names is None:
        #     class_names = [f"Class {k}" for k in range(n_classes)]

        if colors is None:
            # fallback to matplotlib tab10
            base_colors = list(plt.cm.tab10.colors)
        else:
            # pad or cut colors to match number of classes
            if len(colors) < n_classes:
                raise ValueError(
                    f"Need at least {n_classes} colors, got {len(colors)}."
                )
            base_colors = colors[:n_classes]

        fig, ax = plt.subplots(figsize=(8, 0.4 * n_features + 2))

        # stacked bars
        left = np.zeros(n_features)

        for k in range(n_classes):
            ax.barh(
                y=np.arange(n_features),
                width=mean_abs_sorted[:, k],
                left=left,
                color=base_colors[k],
                label=class_names[k],
            )
            left += mean_abs_sorted[:, k]

        ax.set_title("Behavioral Feature Importance Using SHAP")
        ax.set_yticks(np.arange(n_features))
        ax.set_yticklabels(feature_names_sorted)
        ax.invert_yaxis()  # most important on top
        ax.set_xlabel("Average Impact on Model Output Magnitude")
        ax.set_ylabel("Behavioral Feature")
        ax.legend(loc="lower right")
        return fig

    def get_top_n_interactions(
        self, feature_type: FeatureType, class_idx: int, top_n: int = 20
    ) -> list[tuple[tuple[str, str], float]]:
        if self.shap_inter is None:
            raise ValueError(
                "shap_inter is not calculated. Please call self.calculate_feature_interactions() first."
            )

        X_train_vectors, _, _ = get_feature_vectors(
            self.X_train, self.X_val, self.X_test, feature_type
        )
        features = [
            f"{key}: {val}"
            for key, val in get_feature_name(
                feature_type, list(range(len(X_train_vectors[0]))), self.removed_indices
            ).items()
        ]

        pairs = []
        class_interaction_importance = np.abs(self.shap_inter[..., class_idx]).mean(
            axis=0
        )
        n_features = class_interaction_importance.shape[0]

        for i in range(n_features):
            for j in range(i + 1, n_features):
                val = float(class_interaction_importance[i, j])  # scalar
                pairs.append(((features[i], features[j]), val))

        ranked = sorted(pairs, key=lambda x: -x[1])
        return [x for x in ranked[:top_n] if x[1] > 0.0]

    def plot_top_n_interactions(
        self,
        feature_type: FeatureType,
        class_idx: int,
        top_n: int = 20,
    ) -> plt.Figure:
        if self.shap_inter is None:
            raise ValueError(
                "shap_inter is not calculated. Please call self.calculate_feature_interactions() first."
            )

        X_train_vectors, _, _ = get_feature_vectors(
            self.X_train, self.X_val, self.X_test, feature_type
        )
        features = [
            f"{key}: {val}"
            for key, val in get_feature_name(
                feature_type, list(range(len(X_train_vectors[0]))), self.removed_indices
            ).items()
        ]

        pairs = []
        class_interaction_importance = np.abs(self.shap_inter[..., class_idx]).mean(
            axis=0
        )
        n = class_interaction_importance.shape[0]

        for i in range(n):
            for j in range(i + 1, n):
                pairs.append(
                    (features[i], features[j], class_interaction_importance[i, j])
                )

        # Sort descending
        pairs_sorted = sorted(pairs, key=lambda x: -x[2])[:top_n]

        # Plot
        labels = [f"{a} × {b}" for a, b, _ in pairs_sorted]
        values = [v for _, _, v in pairs_sorted]

        plt.figure(figsize=(12, 6))
        plt.barh(labels, values)
        plt.gca().invert_yaxis()
        plt.title(
            f"Top 20 SHAP Feature Interactions – {list(self.dataset.label_mapping.keys())[class_idx]}"
        )
        return plt.gcf()

    def plot_scroll_time_vs_distance(
        self,
        feature_type: FeatureType,
        ax: plt.Axes | None = None,
    ) -> plt.Figure:
        """
        Plot scroll time mean vs scroll distance mean for every feature vector,
        colored by agent.

        Parameters:
            feature_type (FeatureType): Feature type used for classifier.
            ax (matplotlib.axes.Axes, optional): Axes to plot on. If None, creates a new figure.

        Returns:
            fig (matplotlib.figure.Figure): Figure with the plot.
        """
        scroll_time_name = "scroll_time_mean"
        scroll_distance_name = "scroll_distance_mean"

        time_idx = get_feature_index(
            feature_type, scroll_time_name, self.removed_indices
        )[scroll_time_name]
        distance_idx = get_feature_index(
            feature_type, scroll_distance_name, self.removed_indices
        )[scroll_distance_name]

        ordered_agents = sorted(self.dataset.data.keys())
        n_agents = len(ordered_agents)
        palette = plt.cm.tab10(np.linspace(0, 1, max(n_agents, 1)))
        color_by_agent = {agent: palette[i] for i, agent in enumerate(ordered_agents)}

        if ax is None:
            fig, ax = plt.subplots(figsize=(7.16, 3.5))
        else:
            fig = ax.figure

        for agent_type in ordered_agents:
            times = []
            distances = []
            for fvs in self.dataset.data[agent_type].values():
                fpjs_vec = fvs.get("fpjs") if isinstance(fvs, dict) else fvs
                behavioral_vec = fvs.get("behavioral") if isinstance(fvs, dict) else fvs
                combined_vec = fpjs_vec + behavioral_vec

                if feature_type == FeatureType.BEHAVIORAL:
                    t = behavioral_vec[time_idx]
                    d = behavioral_vec[distance_idx]
                elif feature_type == FeatureType.BROWSER:
                    t = fpjs_vec[time_idx]
                    d = fpjs_vec[distance_idx]
                elif feature_type == FeatureType.COMBINED:
                    t = combined_vec[time_idx]
                    d = combined_vec[distance_idx]

                try:
                    t = float(t)
                    d = float(d)
                except (TypeError, ValueError):
                    continue

                if np.isfinite(t) and np.isfinite(d):
                    times.append(t)
                    distances.append(d)

            if times:
                ax.scatter(
                    times,
                    distances,
                    label=agent_type,
                    color=color_by_agent[agent_type],
                    alpha=0.6,
                    s=20,
                )

        ax.set_xlabel("Scroll Time Mean (ms)")
        ax.set_ylabel("Scroll Distance Mean (px)")
        ax.set_title("Scroll Time Mean vs Scroll Distance Mean by Agent")
        ax.legend()
        fig.tight_layout()
        return fig

    def plot_feature_distribution_by_agent_and_task(
        self,
        feature_type: FeatureType,
        feature_name: str,
        y_lim: int = 100,
        fig_size: tuple[float, float] = (7.16, 3.5),
        axes: list[plt.Axes] | None = None,
    ):
        """
        Plot box + strip plots for one feature across agents and tasks.

        Args:
            feature_name: label for the y-axis
        """
        data = self.group_data_by_task()
        agents = [
            "Atlas Agent",
            "Browser Use",
            "Claude",
            "Comet",
            "Skyvern",
            "ChatGPT Agent",
            "Manus",
            "Human",
        ]
        # tasks = list(next(iter(data.values())).keys())
        tasks = ["Flight-booking", "Shopping", "Forums"]

        n_tasks = len(tasks)

        with plt.style.context(["science"]):
            if axes is None:
                _, axes = plt.subplots(1, n_tasks, figsize=fig_size, sharey=True)
                if n_tasks == 1:
                    axes = [axes]

            x_positions = np.arange(len(agents))
            rng = np.random.default_rng(42)

            for ax, task in zip(axes, tasks):
                ax.set_ylim(0, y_lim)
                box_data = []
                for agent in agents:
                    agent_data = []
                    for fvs in data[agent][task]:
                        fpjs_vec = fvs.get("fpjs") if isinstance(fvs, dict) else fvs
                        behavioral_vec = (
                            fvs.get("behavioral") if isinstance(fvs, dict) else fvs
                        )
                        combined_vec = fpjs_vec + behavioral_vec
                        if feature_type == FeatureType.BEHAVIORAL:
                            agent_data.append(
                                behavioral_vec[
                                    get_feature_index(feature_type, feature_name)[
                                        feature_name
                                    ]
                                ]
                            )
                        elif feature_type == FeatureType.BROWSER:
                            agent_data.append(
                                fpjs_vec[
                                    get_feature_index(feature_type, feature_name)[
                                        feature_name
                                    ]
                                ]
                            )
                        elif feature_type == FeatureType.COMBINED:
                            agent_data.append(
                                combined_vec[
                                    get_feature_index(feature_type, feature_name)[
                                        feature_name
                                    ]
                                ]
                            )
                    box_data.append(agent_data)
                # Box plot
                bp = ax.boxplot(
                    box_data,
                    positions=x_positions,
                    widths=0.5,
                    patch_artist=True,
                    showfliers=False,  # outliers shown via strip instead
                    medianprops=dict(color="black", linewidth=1.5),
                    boxprops=dict(facecolor="steelblue", alpha=0.4),
                    whiskerprops=dict(linewidth=1),
                    capprops=dict(linewidth=1),
                )

                # Strip plot overlay
                for i, values in enumerate(box_data):
                    if len(values) == 0:
                        continue
                    jitter = rng.uniform(-0.15, 0.15, size=len(values))
                    ax.scatter(
                        x_positions[i] + jitter,
                        values,
                        alpha=0.15,
                        s=12,
                        color="steelblue",
                        zorder=3,
                    )

                ax.set_title(task, fontsize=11)
                ax.set_xticks(x_positions)
                ax.set_xticklabels(agents, rotation=90, fontsize=9, ha="center")
                ax.grid(axis="y", linestyle="--", alpha=0.4)

            y_label = " ".join(
                [
                    x.capitalize()
                    for x in feature_name.replace("_", " ")
                    .replace("mm", " mouse movement")
                    .replace("num", r"\#")
                    .split()
                ]
            )
            axes[0].set_ylabel(y_label)
            return axes

    def get_agent_feature_stats(
        self,
        feature_type: FeatureType,
        feature_names: dict[str, str | None],
        tasks: list[str] = [],
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Return per-agent stats for each requested feature name.

        Args:
            feature_type (FeatureType): Feature type used for classifier.
            feature_names (dict[str, str | None]): Dictionary mapping feature name to category name or None if not applicable.

        Returns:
            (dict[str, dict[str, dict[str, float]]]): Dictionary mapping agent to dictionary mapping feature
                                                      to dictionary mapping stat name to value.
        """
        if not tasks:
            # Map of agent to map of source to fvs
            data = self.dataset.data
        else:
            # Map of agent to map of idx to fvs
            data = {}
            grouped_data = self.group_data_by_task()
            for agent_type, task_map in grouped_data.items():
                data[agent_type] = {}
                count = 0
                for task in tasks:
                    for x in task_map[task]:
                        data[agent_type][f"{task}_{count}"] = x
                        count += 1

        out = {}
        for agent_type, fvs_map in data.items():
            agent_res = {}
            for feature_name, category_name in feature_names.items():
                name = feature_name
                if category_name is not None:
                    name = f"{feature_name}: {category_name}"
                idx = get_feature_index(feature_type, name)[name]

                collected = []

                for fvs in fvs_map.values():
                    fpjs_vec = fvs.get("fpjs") if isinstance(fvs, dict) else fvs
                    behavioral_vec = (
                        fvs.get("behavioral") if isinstance(fvs, dict) else fvs
                    )
                    combined_vec = fpjs_vec + behavioral_vec

                    if feature_type == FeatureType.BEHAVIORAL:
                        if behavioral_vec[idx] != -1:
                            collected.append(behavioral_vec[idx])
                    elif feature_type == FeatureType.BROWSER:
                        collected.append(fpjs_vec[idx])
                    elif feature_type == FeatureType.COMBINED:
                        if idx < 418 or combined_vec[idx] != -1:
                            collected.append(combined_vec[idx])

                agent_res[feature_name] = summary_stats_1d(
                    (
                        remove_iqr_outliers(collected)
                        # if feature_name
                        # in [
                        #     "interkey_latency_mean",
                        #     "hold_latency_mean",
                        #     "interkey_latency_stdev",
                        #     "hold_latency_stdev",
                        # ]
                        # else collected
                    ),
                )

            out[agent_type] = agent_res

        return out

    def save_shap_matrix(self, output_file: str) -> None:
        """
        Saves SHAP matrices for all test samples.
        Call at step 0 of ablation.

        To load and read SHAP matrices:
        shap_matrix = np.load("results/shap_matrix_baseline.npy")
        shap_matrix[sample_idx, feature_idx, class_idx]
        """
        if self.shap_values is None:
            raise ValueError("Call calculate_shap_values() first.")

        base = output_file.replace(".npy", "")
        np.save(f"{base}.npy", self.shap_values.values)
        np.save(f"{base}_test_labels.npy", self.y_test)

        feature_names = list(
            get_feature_name(
                self.feature_type, list(range(self.shap_values.values.shape[1]))
            ).values()
        )
        class_names = list(self.dataset.label_mapping.keys())

        with open(f"{base}_meta.json", "w") as f:
            json.dump(
                {
                    "feature_names": feature_names,
                    "class_names": class_names,
                },
                f,
                indent=2,
            )


class OVRTrainingPipeline:
    """
    To train a classifier without holdout class:

    pipeline = OVRTrainingPipeline(
        dataset_file="data/dataset.json",
        split_file="data/split.json",
        feature_type=FeatureType.BEHAVIORAL,
    )

    pipeline.get_X_vectors()

    pipeline.train_ovr_manual(model_file="models/model.pkl")

    pipeline.evaluate_ovr_manual()

    ---

    To run the experiment, use scripts/holdout_experiments.py.
    """

    def __init__(
        self,
        dataset_file: str,
        feature_type: FeatureType,
        removed_classes: list[str] = [],
        holdout_classes: list[str] = [],
        seed: int = 32,
    ):
        self.dataset_file = dataset_file
        self.holdout_classes = holdout_classes
        self.removed_classes = removed_classes
        self.seed = seed
        self.dataset = load_dataset(dataset_file, removed_classes)
        self.holdout_dataset = None

        if holdout_classes:
            # Check if holdout class is in dataset
            assert all(
                holdout_class in self.dataset.data.keys()
                for holdout_class in holdout_classes
            ), "holdout class not found in dataset"

            # Create holdout dataset and get dataset split
            self.holdout_dataset = {
                k: v for k, v in self.dataset.data.items() if k in holdout_classes
            }
            if feature_type == FeatureType.BROWSER:
                self.X_holdout_vectors = []
                for fv_list in self.holdout_dataset.values():
                    for fvs in fv_list.values():
                        self.X_holdout_vectors.append(fvs.get("fpjs"))
            elif feature_type == FeatureType.BEHAVIORAL:
                self.X_holdout_vectors = []
                for fv_list in self.holdout_dataset.values():
                    for fvs in fv_list.values():
                        self.X_holdout_vectors.append(fvs.get("behavioral"))
            elif feature_type == FeatureType.COMBINED:
                self.X_holdout_vectors = []
                for fv_list in self.holdout_dataset.values():
                    for fvs in fv_list.values():
                        self.X_holdout_vectors.append(
                            fvs.get("fpjs") + fvs.get("behavioral")
                        )

            self.y_holdout_labels = [
                "unseen" for _ in range(len(self.X_holdout_vectors))
            ]

            # Remove holdout class from dataset
            self.dataset.data = {
                k: v for k, v in self.dataset.data.items() if k not in holdout_classes
            }

        # Get X y split labeled for dataset
        self.X_train, self.X_val, self.X_test, self.y_train, self.y_val, self.y_test = (
            self.dataset.get_split(str_label=True)
        )
        self.feature_type = feature_type

        self.removed_indices: list[int] = []
        self.X_train_vectors = None
        self.X_val_vectors = None
        self.X_test_vectors = None
        self.models: dict[str, xgb.XGBClassifier] = {}
        self.y_pred = None

    def get_X_vectors(self, removed_indices: list[int] = []) -> None:
        """
        Updates removed indices and feature vectors based on the removed indices.
        """

        self.removed_indices = removed_indices

        X_train_vectors, X_val_vectors, X_test_vectors = get_feature_vectors(
            self.X_train, self.X_val, self.X_test, self.feature_type
        )

        self.X_train_vectors = (
            np.delete(X_train_vectors, removed_indices, axis=1)
            if X_train_vectors is not None and len(X_train_vectors) > 0
            else None
        )
        self.X_val_vectors = (
            np.delete(X_val_vectors, removed_indices, axis=1)
            if X_val_vectors is not None and len(X_val_vectors) > 0
            else None
        )
        self.X_test_vectors = (
            np.delete(X_test_vectors, removed_indices, axis=1)
            if X_test_vectors is not None and len(X_test_vectors) > 0
            else None
        )

        # Also remove removed indices from holdout vectors
        if (
            getattr(self, "X_holdout_vectors", None) is not None
            and len(self.X_holdout_vectors) > 0
        ):
            self.X_holdout_vectors = np.delete(
                np.asarray(self.X_holdout_vectors), removed_indices, axis=1
            )

    def train_ovr_manual(
        self,
        model_file: str,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        n_estimators: int = 150,
        use_scale_pos_weight: bool = True,
    ) -> None:
        """Train one binary XGBoost classifier per class (manual OvR)."""

        self.classes = sorted(self.dataset.data.keys())
        y_train = np.asarray(self.y_train)

        for cls in self.classes:
            y_bin = (y_train == cls).astype(int)
            n_pos = int(y_bin.sum())
            n_neg = int(len(y_bin) - n_pos)
            if n_pos == 0:
                raise ValueError(
                    f"Class {cls!r} has no positive samples in training data."
                )

            params = dict(
                max_depth=max_depth,
                learning_rate=learning_rate,
                n_estimators=n_estimators,
                random_state=self.seed,
                eval_metric="logloss",
            )
            if use_scale_pos_weight:
                params["scale_pos_weight"] = n_neg / n_pos

            model = xgb.XGBClassifier(**params)
            model.fit(self.X_train_vectors, y_bin)
            self.models[cls] = model

        if os.path.dirname(model_file) != "":
            os.makedirs(os.path.dirname(model_file), exist_ok=True)
        joblib.dump({"models": self.models, "classes": self.classes}, model_file)

    def load_ovr_manual(self, model_file: str) -> None:
        payload = joblib.load(model_file)
        self.models = payload["models"]
        self.classes = payload["classes"]

    def raw_ovr_probs(self, X) -> np.ndarray:
        """Unnormalized per-class binary probabilities, shape (n_samples, n_classes)."""

        if not getattr(self, "models", None):
            raise ValueError("Model is not trained. Call train_ovr_manual() first.")
        return np.column_stack(
            [self.models[c].predict_proba(X)[:, 1] for c in self.classes]
        )

    def predict_ovr_manual(
        self, X, threshold: float = 0.5, unseen_label: str = "unseen"
    ):
        """Argmax over binary classifiers, rejecting to `unseen_label` if none fire."""

        probs = self.raw_ovr_probs(X)
        preds = np.array(
            [
                (
                    unseen_label
                    if row.max() < threshold
                    else self.classes[int(np.argmax(row))]
                )
                for row in probs
            ],
            dtype=str,
        )
        return preds, probs

    def evaluate_ovr_manual_holdout(
        self,
        X=None,
        y=None,
        threshold: float = 0.5,
        unseen_label: str = "unseen",
    ) -> dict:
        """
        Closed-set OvR evaluation using argmax over binary classifiers with
        thresholded rejection.
        """
        X = self.X_test_vectors if X is None else X
        y = np.asarray(self.y_test if y is None else y, dtype=str)

        preds, _ = self.predict_ovr_manual(
            X, threshold=threshold, unseen_label=unseen_label
        )

        labels = self.classes

        precision_arr, recall_arr, f1_arr, support_arr = (
            precision_recall_fscore_support(
                y, preds, labels=labels, average=None, zero_division=0
            )
        )

        results = {
            "overall": {
                "accuracy": accuracy_score(y, preds),
                "precision": precision_score(
                    y, preds, average="macro", zero_division=0
                ),
                "recall": recall_score(y, preds, average="macro", zero_division=0),
                "f1": f1_score(y, preds, average="macro", zero_division=0),
                "rejection_rate": float(np.mean(preds == unseen_label)),
            },
            "per_class": {
                label: {
                    "precision": float(precision_arr[i]),
                    "recall": float(recall_arr[i]),
                    "f1": float(f1_arr[i]),
                    "support": int(support_arr[i]),
                }
                for i, label in enumerate(labels)
            },
            "confusion_matrix": confusion_matrix(y, preds, labels=labels),
            "labels": labels,
        }
        return results

    def evaluate_ovr_manual(
        self,
        X=None,
        y=None,
    ) -> dict:
        """Closed-set OvR evaluation using argmax over binary classifiers."""

        X = self.X_test_vectors if X is None else X
        y = np.asarray(self.y_test if y is None else y, dtype=str)

        class_indices = self.classes

        probs = self.raw_ovr_probs(X)
        preds = np.array(
            [class_indices[int(np.argmax(row))] for row in probs], dtype=str
        )

        precision_arr, recall_arr, f1_arr, support_arr = (
            precision_recall_fscore_support(
                y, preds, labels=class_indices, average=None, zero_division=0
            )
        )

        return {
            "overall": {
                "accuracy": accuracy_score(y, preds),
                "precision": precision_score(
                    y, preds, average="macro", zero_division=0
                ),
                "recall": recall_score(y, preds, average="macro", zero_division=0),
                "f1": f1_score(y, preds, average="macro", zero_division=0),
            },
            "per_class": {
                # idx_to_name[label]: {
                label: {
                    "precision": float(precision_arr[i]),
                    "recall": float(recall_arr[i]),
                    "f1": float(f1_arr[i]),
                    "support": int(support_arr[i]),
                }
                for i, label in enumerate(class_indices)
            },
            "confusion_matrix": confusion_matrix(y, preds, labels=class_indices),
            "labels": class_indices,
        }

    def fit_with_threshold(
        self,
        model_file: str,
        false_reject_budget: float = 0.05,
        val_frac: float = 0.2,
        **train_kwargs,
    ) -> float:
        """
        Select a rejection threshold without shrinking the training set.

        A temporary model is fit on a subset of the training data and scored on the
        remainder to pick the threshold; the returned model is then refit on the full
        training split.
        """

        X_full, y_full = self.X_train_vectors, self.y_train

        X_tr, X_val, y_tr, _ = train_test_split(
            X_full,
            y_full,
            test_size=val_frac,
            stratify=y_full,
            random_state=self.seed,
        )

        # Fit temporary model on subset of training data to get threshold
        self.X_train_vectors, self.y_train = X_tr, y_tr
        self.train_ovr_manual("/tmp/ovr_threshold_tmp.joblib", **train_kwargs)
        val_scores = self.raw_ovr_probs(X_val).max(axis=1)
        self.threshold = float(np.quantile(val_scores, false_reject_budget))

        # Refit final model on the full training split
        self.X_train_vectors, self.y_train = X_full, y_full
        self.train_ovr_manual(model_file, **train_kwargs)

        self.false_reject_budget = false_reject_budget
        return self.threshold

    def operating_point(
        self,
        threshold: float | None = None,
        unseen_label: str = "unseen",
    ) -> dict:
        """
        Known-class cost and unseen-detection performance at a single threshold.

        Known side: test split (holdout classes already excluded).
        Unseen side: all holdout-class samples.
        """

        if threshold is None:
            threshold = getattr(self, "threshold", None)
            if threshold is None:
                raise ValueError("No threshold. Call fit_with_threshold() first.")

        if self.X_holdout_vectors is None or len(self.X_holdout_vectors) == 0:
            raise ValueError(
                "No holdout data. Construct the pipeline with holdout_classes."
            )

        y_known = np.asarray(self.y_test, dtype=object)

        known_preds, _ = self.predict_ovr_manual(
            self.X_test_vectors, threshold=threshold, unseen_label=unseen_label
        )
        unseen_preds, _ = self.predict_ovr_manual(
            self.X_holdout_vectors, threshold=threshold, unseen_label=unseen_label
        )
        known_preds = known_preds.astype(object)
        unseen_preds = unseen_preds.astype(object)

        # Known-class metrics scored over trained classes only, so they stay
        # directly comparable to the closed-set numbers; a rejected known sample
        # simply misses its class and lowers that class's recall
        known_accuracy = float(np.mean(known_preds == y_known))
        known_macro_f1 = float(
            f1_score(
                y_known,
                known_preds,
                labels=self.classes,
                average="macro",
                zero_division=0,
            )
        )
        false_reject_rate = float(np.mean(known_preds == unseen_label))

        unseen_recall = float(np.mean(unseen_preds == unseen_label))

        # Precision needs both sides pooled and depends on the known/unseen ratio
        all_preds = np.concatenate([known_preds, unseen_preds])
        all_true = np.concatenate(
            [y_known, np.full(len(unseen_preds), unseen_label, dtype=object)]
        )
        flagged = all_preds == unseen_label
        unseen_precision = (
            float(np.mean(all_true[flagged] == unseen_label)) if flagged.any() else 0.0
        )

        return {
            "threshold": float(threshold),
            "false_reject_budget": getattr(self, "false_reject_budget", None),
            "known_accuracy": known_accuracy,
            "known_macro_f1": known_macro_f1,
            "false_reject_rate": false_reject_rate,
            "unseen_recall": unseen_recall,
            "unseen_precision": unseen_precision,
            "unseen_prevalence": float(
                len(unseen_preds) / (len(known_preds) + len(unseen_preds))
            ),
            "n_known": int(len(known_preds)),
            "n_unseen": int(len(unseen_preds)),
        }

    def run_holdout_experiment(
        self,
        model_file: str,
        use_scale_pos_weight: bool = True,
        thresholds=np.linspace(0.1, 0.95, 18),
        unseen_label: str = "unseen",
    ) -> dict:
        """Train excluding `held_out_agent`, then sweep threshold over known vs unseen."""

        self.train_ovr_manual(model_file, use_scale_pos_weight=use_scale_pos_weight)

        curve = []
        for t in thresholds:
            known = self.evaluate_ovr_manual_holdout(
                self.X_test_vectors, self.y_test, threshold=t, unseen_label=unseen_label
            )
            unseen_preds, _ = self.predict_ovr_manual(
                self.X_holdout_vectors, threshold=t, unseen_label=unseen_label
            )
            curve.append(
                {
                    "threshold": float(t),
                    "known_accuracy": known["overall"]["accuracy"],
                    "known_macro_f1": known["overall"]["f1"],
                    "unseen_recall": float(np.mean(unseen_preds == unseen_label)),
                }
            )
        return {"curve": curve, "held_out_classes": self.holdout_classes}

    def get_auroc(self):
        known_scores = self.raw_ovr_probs(self.X_test_vectors).max(axis=1)
        unseen_scores = self.raw_ovr_probs(self.X_holdout_vectors).max(axis=1)

        scores = np.concatenate([known_scores, unseen_scores])
        is_known = np.concatenate(
            [np.ones(len(known_scores)), np.zeros(len(unseen_scores))]
        )

        return roc_auc_score(is_known, scores)

    def open_set_auprc(self, use_margin: bool = False) -> dict:
        """AUPRC for known-vs-unseen detection, reported both directions."""

        if use_margin:
            # Unbounded margins avoid sigmoid saturation
            known_scores = np.column_stack(
                [
                    self.models[c].predict(self.X_test_vectors, output_margin=True)
                    for c in self.classes
                ]
            ).max(axis=1)
            unseen_scores = np.column_stack(
                [
                    self.models[c].predict(self.X_holdout_vectors, output_margin=True)
                    for c in self.classes
                ]
            ).max(axis=1)
        else:
            known_scores = self.raw_ovr_probs(self.X_test_vectors).max(axis=1)
            unseen_scores = self.raw_ovr_probs(self.X_holdout_vectors).max(axis=1)

        scores = np.concatenate([known_scores, unseen_scores])

        # Set unseen as positive class
        # Low max-probability indicates novelty, so negate the score
        y_unseen = np.concatenate(
            [np.zeros(len(known_scores)), np.ones(len(unseen_scores))]
        )
        auprc_unseen = average_precision_score(y_unseen, -scores)

        # Set known as positive class
        y_known = 1 - y_unseen
        auprc_known = average_precision_score(y_known, scores)

        # Baselines: AUPRC of a random classifier = positive class prevalence
        prevalence_unseen = y_unseen.mean()
        prevalence_known = y_known.mean()

        return {
            "auprc_unseen_positive": float(auprc_unseen),
            "auprc_known_positive": float(auprc_known),
            "baseline_unseen": float(prevalence_unseen),
            "baseline_known": float(prevalence_known),
            "n_known": len(known_scores),
            "n_unseen": len(unseen_scores),
        }

    def auprc_at_prevalence(self, target_prev, n_boot=200):
        """AUPRC with unseen subsampled to `target_prev` fraction of the test set."""

        rng = np.random.default_rng(self.seed)
        known_scores = self.raw_ovr_probs(self.X_test_vectors).max(axis=1)
        unseen_scores = self.raw_ovr_probs(self.X_holdout_vectors).max(axis=1)
        n_known = len(known_scores)
        n_unseen_target = int(round(target_prev * n_known / (1 - target_prev)))

        if n_unseen_target > len(unseen_scores):
            raise ValueError(
                f"Need {n_unseen_target} unseen samples for prevalence {target_prev}, "
                f"only have {len(unseen_scores)}"
            )

        vals = []
        for _ in range(n_boot):
            idx = rng.choice(len(unseen_scores), size=n_unseen_target, replace=False)
            s = np.concatenate([known_scores, unseen_scores[idx]])
            y = np.concatenate([np.zeros(n_known), np.ones(n_unseen_target)])
            vals.append(average_precision_score(y, -s))

        return {
            "target_prevalence": target_prev,
            "n_unseen_used": n_unseen_target,
            "auprc_mean": float(np.mean(vals)),
            "auprc_std": float(np.std(vals)),
            "baseline": target_prev,
        }
