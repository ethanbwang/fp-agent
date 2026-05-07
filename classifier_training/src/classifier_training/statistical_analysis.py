import json
import os
from typing import Literal

from dotenv import load_dotenv
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
import orjson
import pandas as pd

load_dotenv()
PROJECT_ROOT = os.getenv("PROJECT_ROOT")


from classifier_training.classifier import TrainingPipeline
from classifier_training.common import remove_iqr_outliers
from classifier_training.data_preprocessing import preprocess_tuple
from classifier_training.data_processing import load_raw_data
from classifier_training.feature_index import get_feature_index
from classifier_training.featurizer import BehavioralFV
from classifier_training.types import FeatureType


def get_ci(data):
    mean = np.mean(data)
    sem = stats.sem(data)  # standard error
    ci = stats.t.interval(0.95, len(data) - 1, loc=mean, scale=sem)
    return mean, ci


def get_all_mean_ci_and_std(
    pipeline: TrainingPipeline, feature: Literal["interkey_latency", "hold_latency"]
) -> dict[str, dict[str, dict[str, float | tuple[float, float]]]]:
    """
    WARNING: Modifies pipeline for Comet hold latency for get_agent_feature_stats to work

    Assumes pipeline is using combined-fingerprint feature set.

    Gets 95% confidence interval for each agent for typing latencies
    Returns:
        dict[str, dict[str, tuple[float, tuple[float, float]]]]: Dictionary mapping
            class name to dictionary mapping feature name to tuple of mean and 95% CI
    """
    out = {}
    feature_idx = get_feature_index(FeatureType.BEHAVIORAL, f"{feature}_mean")[
        f"{feature}_mean"
    ]
    for class_name in pipeline.dataset.data:
        # Browsing agents that don't produce the feature
        SKIP_FEATURES_BY_CLASS = {
            "interkey_latency": {"Atlas Agent", "Comet", "ChatGPT Agent"},
            "hold_latency": {"Atlas Agent"},
        }

        if class_name in SKIP_FEATURES_BY_CLASS.get(feature, set()):
            continue

        out[class_name] = {
            "mean": None,
            "ci": None,
            "std": None,
        }

        if feature == "hold_latency" and class_name == "Comet":
            pipeline.dataset.data["Comet"] = {
                k: v
                for k, v in pipeline.dataset.data["Comet"].items()
                if json.loads(k)["website_version"] == "AGJX7Y80OL"
                and v["behavioral"][feature_idx] != -1
            }

        mean, ci = get_ci(
            remove_iqr_outliers(
                [
                    x["behavioral"][feature_idx]
                    for x in pipeline.dataset.data[class_name].values()
                    if x["behavioral"][feature_idx] != -1
                ]
            )
        )
        out[class_name]["mean"] = mean
        out[class_name]["ci"] = ci

    stds = pipeline.get_agent_feature_stats(
        FeatureType.COMBINED,
        feature_names={
            f"{feature}_stdev": None,
        },
    )
    for class_name in out:
        out[class_name]["std"] = stds[class_name][f"{feature}_stdev"]["mean"]

    return out


def get_raw_scroll_data(
    raw_data_file: str,
) -> dict[str, dict[str, list[tuple[float, float]]]]:
    """
    Get raw scroll data from the raw data file.

    Args:
        raw_data_file (str): Path to raw data file.

    Returns:
        (dict[str, dict[str, list[tuple[float, float]]]]): Dictionary mapping
            class labels to a dictionary mapping task names to a list of tuples
            of scroll duration and scroll distance.
    """
    combined_raw_data = load_raw_data(raw_data_file)
    scroll_data = {}

    for class_label, raw_data_list in combined_raw_data.items():
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

    return scroll_data


def run_mann_whitney_tests(location_pairs, alpha=0.05):
    """
    Args
        location_pairs (list[tuple[str, list[float], str, list[float]]]):
            List of (name_a, data_a, name_b, data_b).
        alpha (float):
            FDR threshold (default 0.05).

    Returns
        (pd.DataFrame): DataFrame with columns:
            family, comparison, U, p_raw, p_adj, r, significant
    """

    def _mwu(pairs, family):
        rows = []
        for name_a, data_a, name_b, data_b in pairs:
            a, b = np.asarray(data_a), np.asarray(data_b)
            u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            r = (2 * u) / (len(a) * len(b)) - 1
            rows.append(
                {
                    "family": family,
                    "comparison": f"{name_a} vs {name_b}",
                    "U": round(u, 2),
                    "p_raw": p,
                    "r": round(r, 3),
                }
            )
        return rows

    loc_rows = _mwu(location_pairs, "location")
    df = pd.DataFrame(loc_rows)

    # BH correction per family
    for family, grp in df.groupby("family"):
        reject, p_adj, _, _ = multipletests(
            grp["p_raw"].values, alpha=alpha, method="fdr_bh"
        )
        df.loc[grp.index, "p_adj"] = p_adj
        df.loc[grp.index, "significant"] = reject

    df["p_raw"] = df["p_raw"].round(5)
    df["p_adj"] = df["p_adj"].round(5)

    return df


def run_levene_tests(pairs, alpha=0.05):
    """
    Args
        pairs (list[tuple[str, list[float], str, list[float]]]):
            List of (name_a, data_a, name_b, data_b).
        alpha (float):
            FDR threshold (default 0.05).

    Returns
        (pd.DataFrame): DataFrame with columns:
            comparison, F, p_raw, p_adj, significant
    """
    rows = []
    for name_a, data_a, name_b, data_b in pairs:
        a, b = np.asarray(data_a), np.asarray(data_b)
        f, p = stats.levene(a, b, center="median")
        rows.append(
            {
                "comparison": f"{name_a} vs {name_b}",
                "F": round(f, 4),
                "p_raw": p,
            }
        )

    df = pd.DataFrame(rows)
    reject, p_adj, _, _ = multipletests(
        df["p_raw"].values, alpha=alpha, method="fdr_bh"
    )
    df["p_adj"] = p_adj.round(5)
    df["p_raw"] = df["p_raw"].round(5)
    df["significant"] = reject

    return df
