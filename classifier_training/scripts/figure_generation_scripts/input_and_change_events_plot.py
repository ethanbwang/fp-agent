import argparse

import matplotlib.pyplot as plt
import numpy as np
import scienceplots

from classifier_training.classifier import TrainingPipeline
from classifier_training.types import FeatureType


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_file", type=str, required=True)
    parser.add_argument("--split_file", type=str, required=True)
    parser.add_argument("--feature_type", type=str, default="BEHAVIORAL")
    parser.add_argument("--removed_classes", type=list, default=[], nargs="+")
    parser.add_argument("--out_file", type=str, required=True)
    args = parser.parse_args()

    feature_type = FeatureType[args.feature_type.upper()]
    pipeline = TrainingPipeline(
        dataset_file=args.dataset_file,
        split_file=args.split_file,
        feature_type=feature_type,
        removed_classes=args.removed_classes,
    )
    pipeline.get_X_vectors()

    with plt.style.context(["science"]):
        with plt.rc_context({"font.size": 8}):
            fig, axes = plt.subplots(
                2,
                3,
                figsize=(7.16, 3.5),
                sharey="row",
                sharex=True,
                layout="constrained",
                gridspec_kw={"height_ratios": [2, 1]},
            )

            pipeline.plot_feature_distribution_by_agent_and_task(
                feature_type,
                "num_input_events",
                fig_size=(7.16, 2.5),
                axes=axes[0],
            )
            pipeline.plot_feature_distribution_by_agent_and_task(
                feature_type,
                "num_change_events",
                fig_size=(7.16, 2.5),
                axes=axes[1],
            )

            for ax in axes.flatten():
                ax.tick_params(which="both", top=False)
                ax.tick_params(which="both", bottom=False)

            for ax in axes[0]:
                ax.set_ylim(0, 2000)
                ax.set_yticks(np.arange(0, 2001, 500))
                ax.set_yticks(np.arange(0, 2001, 125), minor=True)
                ax.title.set_fontsize(9)

            for ax in axes[1]:
                ax.set_title("")
                ax.set_ylim(0, 80)
                ax.set_yticks(np.arange(0, 81, 20))
                ax.set_yticks(np.arange(0, 81, 10), minor=True)
                for lab in ax.get_yticklabels():
                    lab.set_fontsize(8)

            axes[1][0].set_ylabel(r"\# Change Events", labelpad=13)

    fig.savefig(args.out_file, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
