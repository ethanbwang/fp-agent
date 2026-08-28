import argparse

import matplotlib.pyplot as plt
import scienceplots

from classifier_training.classifier import TrainingPipeline
from classifier_training.types import FeatureType


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_file", type=str, required=True)
    parser.add_argument("--split_file", type=str, required=True)
    parser.add_argument("--removed_classes", type=list, default=[], nargs="+")
    parser.add_argument("--browser_classifier", type=str, required=True)
    parser.add_argument("--behavioral_classifier", type=str, required=True)
    parser.add_argument("--combined_classifier", type=str, required=True)
    parser.add_argument("--out_file", type=str, required=True)
    args = parser.parse_args()

    fpjs_pipeline = TrainingPipeline(
        dataset_file=args.dataset_file,
        split_file=args.split_file,
        feature_type=FeatureType.BROWSER,
        removed_classes=args.removed_classes,
    )
    fpjs_pipeline.load_model(f"{args.browser_classifier}")
    fpjs_pipeline.get_X_vectors()

    behavioral_pipeline = TrainingPipeline(
        dataset_file=args.dataset_file,
        split_file=args.split_file,
        feature_type=FeatureType.BEHAVIORAL,
        removed_classes=args.removed_classes,
    )
    behavioral_pipeline.load_model(f"{args.behavioral_classifier}")
    behavioral_pipeline.get_X_vectors()

    combined_pipeline = TrainingPipeline(
        dataset_file=args.dataset_file,
        split_file=args.split_file,
        feature_type=FeatureType.COMBINED,
        removed_classes=args.removed_classes,
    )
    combined_pipeline.load_model(f"{args.combined_classifier}")
    combined_pipeline.get_X_vectors()

    fpjs_pipeline.evaluate_model()
    behavioral_pipeline.evaluate_model()
    combined_pipeline.evaluate_model()

    with plt.style.context(["science"]):
        with plt.rc_context({"font.size": 8}):
            fig, axes = plt.subplots(1, 3, figsize=(7.16, 3.08), sharey=True)

            axes.flatten()

            for ax, pipeline in zip(
                axes, [fpjs_pipeline, behavioral_pipeline, combined_pipeline]
            ):
                pipeline.display_confusion_matrix(ax=ax)
                ax.set_aspect("auto")

            axes[0].set_title("Browser Fingerprint")
            axes[1].set_title("Behavioral Fingerprint")
            axes[2].set_title("Combined")

            axes[1].set_ylabel("")
            axes[2].set_ylabel("")

            fig.tight_layout()
            fig.savefig(args.out_file, bbox_inches="tight", dpi=300)


if __name__ == "__main__":
    main()
