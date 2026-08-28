import argparse

import matplotlib.pyplot as plt
import orjson
import scienceplots

from classifier_training.data_processing import load_raw_data
from classifier_training.data_preprocessing import preprocess_tuple
from classifier_training.featurizer import BehavioralFV


from statistics import median
import matplotlib.pyplot as plt
import numpy as np


def plot_scroll_data(
    scroll_data: dict[str, dict[str, list[tuple[float, float]]]],
) -> plt.Figure:
    classes = [
        "Atlas Agent",
        "Browser Use",
        "Claude",
        "Comet",
        "Skyvern",
        "ChatGPT Agent",
        "Manus",
        "Human",
    ]

    task_colors = {
        "Flight-booking": "#ff7f0e",
        "Shopping": "#2ca02c",
        "Forums": "#1f77b4",
    }

    ncols, nrows = 4, 2

    legend_handles = []
    legend_labels = []

    marker = "o"

    with plt.style.context(["science"]):
        with plt.rc_context({"font.size": 8, "font.family": "DejaVu Sans"}):
            fig, axes = plt.subplots(
                nrows,
                ncols,
                figsize=(7.18, 3.09),
                sharex=True,
                sharey=True,
                gridspec_kw={"hspace": 0, "wspace": 0},  # no padding between subplots
            )
            axes = axes.flatten()

            for i, cls in enumerate(classes):
                ax = axes[i]
                all_duration = []
                all_distance = []
                for task in scroll_data[cls].keys():
                    subset = [
                        x for x in scroll_data[cls][task] if x[0] < 1000 and x[1] < 3000
                    ]
                    duration = [x[0] for x in subset]
                    distance = [x[1] for x in subset]
                    all_duration.extend(duration)
                    all_distance.extend(distance)
                    scatter = ax.scatter(
                        duration,
                        distance,
                        marker=marker,
                        alpha=0.2,
                        s=3,
                        color=task_colors[task],
                        edgecolors=task_colors[task],
                        rasterized=True,
                        label=task if i == 0 else "",
                    )
                    if i == 0:
                        legend_handles.append(scatter)
                        legend_labels.append(task)

                ax.axvline(
                    median(all_duration), color="grey", lw=0.8, ls="--", alpha=0.7
                )
                ax.axhline(
                    median(all_distance), color="grey", lw=0.8, ls="--", alpha=0.7
                )

                # Title in top-right corner as text annotation
                ax.text(
                    0.97,
                    0.97,
                    cls,
                    transform=ax.transAxes,
                    ha="right",
                    va="top",
                    fontsize=8,
                    bbox=dict(
                        boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8
                    ),
                )

                ax.set_xlabel("Duration (ms)" if i >= 4 else "")
                ax.set_ylabel("Distance (px)" if i % 4 == 0 else "")
                ax.set_xticks(np.arange(0, 1001, 250))
                ax.set_xticks(np.arange(0, 1126, 125), minor=True)
                ax.tick_params(axis="x", which="major", length=3.5)
                ax.tick_params(axis="x", which="minor", length=2)
                ax.tick_params(axis="y", which="major", length=3.5)
                ax.tick_params(axis="y", which="minor", length=2)

                ax.tick_params(which="both", right=False, top=False)
                # Keep all spines visible for the box effect
                ax.spines[["top", "right", "bottom", "left"]].set_visible(True)

                # Hide tick labels on inner edges to avoid clutter
                if i % 4 != 0:
                    ax.tick_params(labelleft=False)
                if i < 4:
                    ax.tick_params(labelbottom=False)

            legend_dict = dict(zip(legend_labels, legend_handles))
            label_order = ["Flight-booking", "Shopping", "Forums"]

            legend = fig.legend(
                handles=[legend_dict[label] for label in label_order],
                labels=label_order,
                loc="lower center",
                bbox_to_anchor=(0.5, 0.88),
                ncol=4,
                frameon=True,  # box around legend
                handleheight=1.2,
                markerscale=3,
            )

            for handle in legend.legend_handles:
                handle.set_alpha(1.0)

            return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_data_file", type=str, required=True)
    parser.add_argument("--out_file", type=str, required=True)
    args = parser.parse_args()

    raw_data = load_raw_data(args.raw_data_file)
    scroll_data = {}

    for class_label, raw_data_list in raw_data.items():
        scroll_data[class_label] = {}
        for raw_data in raw_data_list:
            events = []
            task_name = raw_data.source.task_name.split()[0]
            if task_name not in scroll_data[class_label]:
                scroll_data[class_label][task_name] = []

            for raw_behavioral_data in raw_data.behavioral_data:
                req_body = orjson.loads(raw_behavioral_data.req_body)
                if "eventFrames" in req_body:
                    # Convert lists to tuples and preprocess
                    event_frames = [
                        preprocess_tuple(tuple(event))
                        for event in req_body["eventFrames"]
                    ]
                    events.extend(event_frames)

            behavioral_feature_vector = BehavioralFV()
            behavioral_feature_vector.parse_events(events)
            scroll_data[class_label][
                task_name
            ] += behavioral_feature_vector.get_all_scroll_data()

    fig = plot_scroll_data(scroll_data)

    fig.savefig(args.out_file, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
