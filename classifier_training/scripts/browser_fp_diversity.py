"""
Computes browser fingerprint diversity metrics:
- Number of unique fingerprints
- top-k coverage
- normalized Shannon entropy

Usage:
uv run scripts/browser_fp_diversity.py --dataset_file <dataset_file>
"""

import argparse
from collections import Counter
import logging
from typing import Any

import numpy as np
import pandas as pd

from classifier_training.common import load_dataset


def top_k_coverage(fingerprints: list[Any], k: int) -> float:
    """
    Fraction of sessions accounted for by the k most common fingerprints.

    Args:
        fingerprints (list[Any]): One fingerprint value per session (strings, ints, tuples, etc.)
        k (int): Number of top fingerprints to include.

    Returns:
        (float): Fraction of sessions accounted for by the k most common fingerprints.
    """
    if not fingerprints:
        return float("nan")
    counts = Counter(fingerprints)
    top_k_counts = sorted(counts.values(), reverse=True)[:k]
    return sum(top_k_counts) / len(fingerprints)


def shannon_entropy(fingerprints: list[Any], normalized: bool = True) -> float:
    """
    Shannon entropy of the fingerprint distribution for a class.

    Args:
        fingerprints (list[Any]): One fingerprint value per session.
        normalized (bool): If True, divide by log2(n_unique) so the result is in [0, 1].
            If False, return raw entropy in bits.

    Returns:
        (float): Fraction of sessions accounted for by the top k most common fingerprints.
    """
    if not fingerprints:
        return float("nan")

    counts = np.array(list(Counter(fingerprints).values()), dtype=float)
    n_unique = len(counts)
    if n_unique == 1:
        return 0.0

    probs = counts / counts.sum()
    raw_entropy = -np.sum(probs * np.log2(probs))
    if normalized:
        return raw_entropy / np.log2(n_unique)
    return raw_entropy


def fingerprint_metrics_table(
    data: dict[str, list[Any]],
    k: int = 1,
) -> pd.DataFrame:
    """
    Builds per-class metrics table.

    Args:
        data (dict[str, list]): Mapping of class name to list of fingerprint values.
        k (int): k for top-k coverage.

    Returns:
        (pd.DataFrame): DataFrame with columns:
        class               - class name
        sessions            - total number of sessions
        unique_fingerprints - number of distinct fingerprints
        top_{k}_coverage    - fraction of sessions covered by top-k fingerprints
        entropy_normalized  - normalized Shannon entropy (0 = concentrated, 1 = uniform)
    """
    rows = []
    for cls, fingerprints in data.items():
        n_sessions = len(fingerprints)
        n_unique = len(set(fingerprints))
        coverage = top_k_coverage(fingerprints, k)
        entropy = shannon_entropy(fingerprints, normalized=True)
        rows.append(
            {
                "class": cls,
                "sessions": n_sessions,
                "unique_fingerprints": n_unique,
                f"top_{k}_coverage": round(coverage, 4),
                "entropy_normalized": round(entropy, 4),
            }
        )

    df = pd.DataFrame(rows)

    # Warn if k exceeds the minimum unique fingerprint count
    min_unique = df["unique_fingerprints"].min()
    if k > min_unique:
        logger.warning(
            f"k={k} exceeds the minimum unique fingerprint count ({min_unique}) "
            f"across classes. Top-{k} coverage will be 1.0 for that class by "
            f"definition and may not be comparable across rows. Consider k <= {min_unique}."
        )

    return df


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    args = argparse.ArgumentParser()
    args.add_argument(
        "--dataset_file", type=str, required=True, help="Path to dataset file."
    )
    args.add_argument("--k", type=int, default=1, help="Top-k coverage parameter.")
    args.add_argument("--out_file", type=str, help="Output file for metrics table.")
    args = args.parse_args()

    dataset = load_dataset(args.dataset_file)
    fpjs_fingerprints = {}
    for class_label, data in dataset.data.items():
        fpjs_fingerprints[class_label] = []
        for source, fvs in data.items():
            fpjs_fingerprints[class_label].append(tuple(fvs["fpjs"]))
    table = fingerprint_metrics_table(fpjs_fingerprints, k=1)

    if args.out_file is not None:
        table.to_csv(args.out_file, index=False)
    else:
        print(table.to_string(index=False))
