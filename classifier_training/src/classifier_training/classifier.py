from collections import defaultdict
import os
import json


from dotenv import load_dotenv

load_dotenv()


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# import scienceplots
import shap
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
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
