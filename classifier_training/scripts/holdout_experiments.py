"""
Run holdout experiments for a given dataset, feature type, and k-holdout.
"""

import argparse
import itertools
import logging
import os
import traceback

import pandas as pd
from tqdm import tqdm

from classifier_training.classifier import OVRTrainingPipeline
from classifier_training.common import load_dataset
from classifier_training.types import FeatureType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_file", type=str, required=True)
    parser.add_argument("--feature_type", type=str, required=True)
    parser.add_argument("--k_holdout", type=int, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--frr_budget", type=float, default=0.05)
    parser.add_argument("--use_scale_pos_weight", action="store_true")
    parser.add_argument(
        "--keep_models",
        action="store_true",
        help="Persist per-fold model files instead of writing to a scratch path.",
    )
    parser.add_argument("--seed", type=int, default=32)
    args = parser.parse_args()

    feature_type = FeatureType[args.feature_type.upper()]

    # Get combinations of agents to hold out
    classes = sorted(
        load_dataset(args.dataset_file, removed_classes=["Human"]).data.keys()
    )
    combinations = list(itertools.combinations(classes, args.k_holdout))
    logger.info(
        f"{len(classes)} classes, k={args.k_holdout} -> {len(combinations)} folds"
    )

    os.makedirs(args.output_dir, exist_ok=True)

    rows = []
    for idx, combination in tqdm(
        enumerate(combinations),
        desc=f"Running holdout experiments at k={args.k_holdout}",
    ):
        held = list(combination)
        tag = "+".join(held).replace(" ", "_").replace("/", "_")
        logger.info(f"[{idx}/{len(combinations)}] holding out: {', '.join(held)}")

        model_file = (
            f"{args.output_dir}/models/holdout_{tag}.pkl"
            if args.keep_models
            else f"/tmp/ovr_holdout_{tag}.pkl"
        )

        try:
            pipeline = OVRTrainingPipeline(
                dataset_file=args.dataset_file,
                feature_type=feature_type,
                holdout_classes=held,
                seed=args.seed,
            )
            pipeline.get_X_vectors()

            pipeline.fit_with_threshold(
                model_file,
                false_reject_budget=args.frr_budget,
                use_scale_pos_weight=args.use_scale_pos_weight,
            )

            auroc = pipeline.get_auroc()
            auprc = pipeline.open_set_auprc()
            op = pipeline.operating_point()

            rows.append(
                {
                    "held_out": "+".join(held),
                    "k": args.k_holdout,
                    "auroc": auroc,
                    "auprc_unseen": auprc["auprc_unseen_positive"],
                    "baseline": auprc["baseline_unseen"],
                    "lift": auprc["auprc_unseen_positive"] / auprc["baseline_unseen"],
                    "unseen_recall": op["unseen_recall"],
                    "unseen_precision": op["unseen_precision"],
                    "known_acc": op["known_accuracy"],
                    "known_macro_f1": op["known_macro_f1"],
                    "frr_budget": args.frr_budget,
                    "frr_realized": op["false_reject_rate"],
                    "threshold": op["threshold"],
                    "n_known": auprc["n_known"],
                    "n_unseen": auprc["n_unseen"],
                }
            )
        except Exception:
            logger.error(f"  FAILED on {held}:")
            traceback.print_exc()
            continue

    if not rows:
        logging.warning("No successful folds.")
        return

    df = pd.DataFrame(rows)
    per_fold = f"{args.output_dir}/open_set_k{args.k_holdout}.csv"
    df.to_csv(per_fold, index=False)

    # Summary row
    metric_cols = [
        "auroc",
        "auprc_unseen",
        "baseline",
        "lift",
        "unseen_recall",
        "unseen_precision",
        "known_acc",
        "known_macro_f1",
        "frr_realized",
    ]
    summary = pd.DataFrame(
        [
            {
                "k": args.k_holdout,
                "n_folds": len(df),
                **{f"{c}_mean": df[c].mean() for c in metric_cols},
                **{f"{c}_std": df[c].std(ddof=1) for c in metric_cols},
            }
        ]
    )
    summary_file = f"{args.output_dir}/open_set_summary_k{args.k_holdout}.csv"
    summary.to_csv(summary_file, index=False)

    logging.info(f"\nwrote {per_fold} ({len(df)} folds)")
    logging.info(f"wrote {summary_file}")
    logging.info(
        f"AUROC {df['auroc'].mean():.3f} ± {df['auroc'].std(ddof=1):.3f} | "
        f"AUPRC {df['auprc_unseen'].mean():.3f} ± {df['auprc_unseen'].std(ddof=1):.3f} | "
        f"recall@{args.frr_budget:.0%}FRR {df['unseen_recall'].mean():.3f}"
    )


if __name__ == "__main__":
    main()
