import argparse
import json

from dotenv import load_dotenv
import numpy as np
import os
import pandas as pd

from classifier_training.classifier import TrainingPipeline
from classifier_training.common import remove_iqr_outliers
from classifier_training.feature_index import get_feature_index
from classifier_training.statistical_analysis import (
    get_all_mean_ci_and_std,
    run_mann_whitney_tests,
    run_levene_tests,
    get_raw_scroll_data,
)
from classifier_training.types import FeatureType

load_dotenv()

PROJECT_ROOT = os.getenv("PROJECT_ROOT")


def mean_ci_and_std_analysis(args) -> None:
    pipeline = TrainingPipeline(
        dataset_file=args.dataset_file,
        split_file=args.split_file,
        feature_type=FeatureType.COMBINED,
        removed_classes=[],
    )

    print("Interkey latency:")
    print(get_all_mean_ci_and_std(pipeline, "interkey_latency"))

    pipeline = TrainingPipeline(
        dataset_file=args.dataset_file,
        split_file=args.split_file,
        feature_type=FeatureType.COMBINED,
        removed_classes=[],
    )
    print("--------------------------------")
    print("Hold latency:")
    print(get_all_mean_ci_and_std(pipeline, "hold_latency"))


def _get_pairs(
    args,
) -> tuple[
    list[tuple[str, list[float], str, list[float]]],
    list[tuple[str, list[float], str, list[float]]],
]:
    pipeline = TrainingPipeline(
        dataset_file=args.dataset_file,
        split_file=args.split_file,
        feature_type=FeatureType.COMBINED,
        removed_classes=[],
    )

    scroll_data = get_raw_scroll_data(args.raw_data_file)

    # Font preferences
    font_prefs: dict[str, list[float]] = {}
    font_prefs_idx = get_feature_index(FeatureType.BROWSER, "fontApple")["fontApple"]
    for agent in pipeline.dataset.data:
        font_prefs[agent] = [
            x["fpjs"][font_prefs_idx] for x in pipeline.dataset.data[agent].values()
        ]

    # Font preferences for Comet, Claude, Atlas, Browser Use on MacOS
    font_prefs_mac = {}
    agent_mac_vers = {
        "Comet": "ECQXUPCKC0",
        "Claude": "4235VTOXWV",
        "Browser Use": "2GH0XXEN6Q",
        "Atlas Agent": "16DVHC3NBI",
    }
    for agent in agent_mac_vers.keys():
        font_prefs_mac[agent] = []
        for source, fps in pipeline.dataset.data[agent].items():
            if json.loads(source)["website_version"] == agent_mac_vers[agent]:
                font_prefs_mac[agent].append(fps["fpjs"][font_prefs_idx])

    # Hold and interkey latencies (Mann-Whitney for both mean and variance)
    typing_classes = ["Browser Use", "Human", "Manus"]
    non_typing_classes = ["Comet", "Atlas Agent", "Skyvern", "ChatGPT Agent"]
    feature_indices = get_feature_index(
        FeatureType.BEHAVIORAL,
        [
            "interkey_latency_mean",
            "hold_latency_mean",
            "interkey_latency_stdev",
            "hold_latency_stdev",
        ],
    )
    ikl_mean_idx = feature_indices["interkey_latency_mean"]
    ikl_stdev_idx = feature_indices["interkey_latency_stdev"]
    hl_mean_idx = feature_indices["hold_latency_mean"]
    hl_stdev_idx = feature_indices["hold_latency_stdev"]

    interkey_latency_means = {}
    interkey_latency_stdevs = {}
    hold_latency_means = {}
    hold_latency_stdevs = {}
    for agent in typing_classes + ["Skyvern", "Claude"]:
        interkey_latency_means[agent] = []
        interkey_latency_stdevs[agent] = []
        hold_latency_means[agent] = []
        hold_latency_stdevs[agent] = []
        for fvs in pipeline.dataset.data[agent].values():
            if fvs["behavioral"][ikl_mean_idx] != -1:
                interkey_latency_means[agent].append(fvs["behavioral"][ikl_mean_idx])
            if fvs["behavioral"][ikl_stdev_idx] != -1:
                interkey_latency_stdevs[agent].append(fvs["behavioral"][ikl_stdev_idx])
            if fvs["behavioral"][hl_mean_idx] != -1:
                hold_latency_means[agent].append(fvs["behavioral"][hl_mean_idx])
            if fvs["behavioral"][hl_stdev_idx] != -1:
                hold_latency_stdevs[agent].append(fvs["behavioral"][hl_stdev_idx])

        interkey_latency_means[agent] = np.array(
            remove_iqr_outliers(interkey_latency_means[agent])
        )
        interkey_latency_stdevs[agent] = np.array(
            remove_iqr_outliers(interkey_latency_stdevs[agent])
        )
        hold_latency_means[agent] = np.array(
            remove_iqr_outliers(hold_latency_means[agent])
        )
        hold_latency_stdevs[agent] = np.array(
            remove_iqr_outliers(hold_latency_stdevs[agent])
        )

    interkey_latency_means["Claude"] = []
    interkey_latency_stdevs["Claude"] = []
    hold_latency_means["Claude"] = []
    hold_latency_stdevs["Claude"] = []
    for fvs in pipeline.dataset.data["Claude"].values():
        if fvs["behavioral"][ikl_mean_idx] != -1:
            interkey_latency_means["Claude"].append(fvs["behavioral"][ikl_mean_idx])
        if fvs["behavioral"][ikl_stdev_idx] != -1:
            interkey_latency_stdevs["Claude"].append(fvs["behavioral"][ikl_stdev_idx])
        if fvs["behavioral"][hl_mean_idx] != -1:
            hold_latency_means["Claude"].append(fvs["behavioral"][hl_mean_idx])
        if fvs["behavioral"][hl_stdev_idx] != -1:
            hold_latency_stdevs["Claude"].append(fvs["behavioral"][hl_stdev_idx])

    interkey_latency_means["Claude"] = np.array(
        remove_iqr_outliers(interkey_latency_means["Claude"])
    )
    interkey_latency_stdevs["Claude"] = np.array(
        remove_iqr_outliers(interkey_latency_stdevs["Claude"])
    )
    hold_latency_means["Claude"] = np.array(
        remove_iqr_outliers(hold_latency_means["Claude"])
    )
    hold_latency_stdevs["Claude"] = np.array(
        remove_iqr_outliers(hold_latency_stdevs["Claude"])
    )

    # Comet
    relevant_comet_data = {
        k: v
        for k, v in pipeline.dataset.data["Comet"].items()
        if json.loads(k)["website_version"] == "AGJX7Y80OL"
        and v["behavioral"][hl_mean_idx] != -1
    }

    comet_hold_latency_means = np.array(
        remove_iqr_outliers(
            [x["behavioral"][hl_mean_idx] for x in relevant_comet_data.values()]
        )
    )

    comet_hold_latency_stdevs = np.array(
        remove_iqr_outliers(
            [x["behavioral"][hl_stdev_idx] for x in relevant_comet_data.values()]
        )
    )

    # ChatGPT Agent
    hold_latency_means["ChatGPT Agent"] = []
    hold_latency_stdevs["ChatGPT Agent"] = []
    for fvs in pipeline.dataset.data["ChatGPT Agent"].values():
        if fvs["behavioral"][hl_mean_idx] != -1:
            hold_latency_means["ChatGPT Agent"].append(fvs["behavioral"][hl_mean_idx])
        if fvs["behavioral"][hl_stdev_idx] != -1:
            hold_latency_stdevs["ChatGPT Agent"].append(fvs["behavioral"][hl_stdev_idx])

    hold_latency_means["ChatGPT Agent"] = np.array(
        remove_iqr_outliers(hold_latency_means["ChatGPT Agent"])
    )
    hold_latency_stdevs["ChatGPT Agent"] = np.array(
        remove_iqr_outliers(hold_latency_stdevs["ChatGPT Agent"])
    )

    # Scroll duration and distance
    scroll_durations = {}
    scroll_distances = {}

    for agent in scroll_data:
        scroll_durations[agent] = []
        scroll_distances[agent] = []
        for task in scroll_data[agent]:
            scroll_durations[agent].extend([x[0] for x in scroll_data[agent][task]])
            scroll_distances[agent].extend([x[1] for x in scroll_data[agent][task]])

    # Number of change events
    num_change_events = {}
    num_change_events_idx = get_feature_index(
        FeatureType.BEHAVIORAL, "num_change_events"
    )["num_change_events"]
    for agent in pipeline.dataset.data:
        num_change_events[agent] = [
            x["behavioral"][num_change_events_idx]
            for x in pipeline.dataset.data[agent].values()
        ]

    # Number of input events
    num_input_events = {
        "typing": [],
        "non_typing": [],
    }
    num_input_events_idx = get_feature_index(
        FeatureType.BEHAVIORAL, "num_input_events"
    )["num_input_events"]
    for cls in typing_classes:
        for x in pipeline.dataset.data[cls].values():
            num_input_events["typing"].append(x["behavioral"][num_input_events_idx])

    for cls in non_typing_classes:
        for x in pipeline.dataset.data[cls].values():
            num_input_events["non_typing"].append(x["behavioral"][num_input_events_idx])

    by_task = pipeline.group_data_by_task()

    for task in ["Shopping", "Flight-booking"]:
        for x in by_task["Claude"][task]:
            num_input_events["non_typing"].append(x["behavioral"][num_input_events_idx])

    for x in by_task["Claude"]["Forums"]:
        num_input_events["non_typing"].append(x["behavioral"][num_input_events_idx])

    ### Pairs
    all_ikl_agents_no_human = list(interkey_latency_means.keys())
    all_ikl_agents_no_human.remove("Human")
    all_hl_agents_no_human = list(hold_latency_means.keys())
    all_hl_agents_no_human.remove("Human")
    all_scr_agents_no_human = list(scroll_durations.keys())
    all_scr_agents_no_human.remove("Human")
    all_chg_agents = list(num_change_events.keys())
    all_chg_agents.remove("Human")
    all_chg_agents.remove("Browser Use")

    other_font_prefs = []
    for x in [
        "Atlas Agent",
        "Browser Use",
        "Claude",
        "Comet",
        "Skyvern",
        "Manus",
        "Human",
    ]:
        other_font_prefs.extend(font_prefs[x])

    other_mac_font_prefs = []
    for x in ["Atlas Agent", "Browser Use", "Claude"]:
        other_mac_font_prefs.extend(font_prefs_mac[x])

    all_ikl_agents_no_human_ikl_means = []
    for x in all_ikl_agents_no_human:
        all_ikl_agents_no_human_ikl_means.extend(interkey_latency_means[x])

    all_ikl_agents_no_human_ikl_stdevs = []
    for x in all_ikl_agents_no_human:
        all_ikl_agents_no_human_ikl_stdevs.extend(interkey_latency_stdevs[x])

    all_hold_agents_no_human_hold_means = []
    for x in all_hl_agents_no_human:
        all_hold_agents_no_human_hold_means.extend(hold_latency_means[x])
    all_hold_agents_no_human_hold_means.extend(comet_hold_latency_means)

    all_hold_agents_no_human_hold_stdevs = []
    for x in all_hl_agents_no_human:
        all_hold_agents_no_human_hold_stdevs.extend(hold_latency_stdevs[x])
    all_hold_agents_no_human_hold_stdevs.extend(comet_hold_latency_stdevs)

    all_scroll_agents_no_human_scroll_duration_means = []
    for x in all_scr_agents_no_human:
        if x != "ChatGPT Agent":
            all_scroll_agents_no_human_scroll_duration_means.extend(scroll_durations[x])

    all_scroll_agents_no_human_scroll_distance_means = []
    for x in all_scr_agents_no_human:
        if x != "ChatGPT Agent":
            all_scroll_agents_no_human_scroll_distance_means.extend(scroll_distances[x])

    all_change_events_other_agents = []
    for x in all_chg_agents:
        all_change_events_other_agents.extend(num_change_events[x])

    agent_hold_latency_compare = []
    for x in all_hl_agents_no_human:
        if x not in ["ChatGPT Agent", "Manus"]:
            agent_hold_latency_compare.extend(hold_latency_means[x])

    mw_pairs = [
        (
            "ChatGPT Agent font prefs",
            font_prefs["ChatGPT Agent"],
            "Other",
            other_font_prefs,
        ),
        (
            "Comet font prefs",
            font_prefs_mac["Comet"],
            "Atlas Agent, Browser Use, Claude",
            other_mac_font_prefs,
        ),
        (
            "Human IKL mean",
            interkey_latency_means["Human"],
            ", ".join(all_ikl_agents_no_human),
            all_ikl_agents_no_human_ikl_means,
        ),
        (
            "Human IKL stdev",
            interkey_latency_stdevs["Human"],
            ", ".join(all_ikl_agents_no_human),
            all_ikl_agents_no_human_ikl_stdevs,
        ),
        (
            "Human hold mean",
            hold_latency_means["Human"],
            ", ".join(all_hl_agents_no_human + ["Comet"]),
            all_hold_agents_no_human_hold_means,
        ),
        (
            "Human hold stdev",
            hold_latency_stdevs["Human"],
            ", ".join(all_hl_agents_no_human + ["Comet"]),
            all_hold_agents_no_human_hold_stdevs,
        ),
        (
            "Human scroll duration mean",
            scroll_durations["Human"],
            "Other (excl. ChatGPT Agent)",
            all_scroll_agents_no_human_scroll_duration_means,
        ),
        (
            "ChatGPT Agent scroll duration mean",
            scroll_durations["ChatGPT Agent"],
            "Human",
            scroll_durations["Human"],
        ),
        (
            "Human scroll distance means",
            scroll_distances["Human"],
            "Other (excl. ChatGPT Agent)",
            all_scroll_agents_no_human_scroll_distance_means,
        ),
        (
            "ChatGPT Agent scroll distance means",
            scroll_distances["ChatGPT Agent"],
            "Human",
            scroll_distances["Human"],
        ),
        (
            "Browser Use num change",
            num_change_events["Browser Use"],
            "Other Agents",
            all_change_events_other_agents,
        ),
        (
            "Typing",
            num_input_events["typing"],
            "Non-Typing",
            num_input_events["non_typing"],
        ),
        (
            "ChatGPT Agent hold latency means",
            hold_latency_means["ChatGPT Agent"],
            "Comet",
            comet_hold_latency_means,
        ),
        (
            "Manus hold latency means",
            hold_latency_means["Manus"],
            "Other",
            agent_hold_latency_compare,
        ),
        (
            "ChatGPT Agent hold latency means",
            hold_latency_means["ChatGPT Agent"],
            "Other",
            agent_hold_latency_compare,
        ),
        (
            "ChatGPT Agent scroll distance means",
            scroll_distances["ChatGPT Agent"],
            "Atlas, Browser Use, Claude, Comet",
            scroll_distances["Atlas Agent"]
            + scroll_distances["Browser Use"]
            + scroll_distances["Claude"]
            + scroll_distances["Comet"],
        ),
        (
            "ChatGPT Agent scroll duration means",
            scroll_durations["ChatGPT Agent"],
            "Atlas, Browser Use, Claude, Comet",
            scroll_durations["Atlas Agent"]
            + scroll_durations["Browser Use"]
            + scroll_durations["Claude"]
            + scroll_durations["Comet"],
        ),
    ]

    levene_pairs = [
        (
            "Human scroll duration",
            [x for x in scroll_durations["Human"] if x < 1000],
            ag,
            [x for x in scroll_durations[ag] if x < 1000],
        )
        for ag in all_scr_agents_no_human
    ] + [
        (
            "Human scroll distance",
            [x for x in scroll_distances["Human"] if x < 3000],
            ag,
            [x for x in scroll_distances[ag] if x < 3000],
        )
        for ag in all_scr_agents_no_human
    ]

    return mw_pairs, levene_pairs


def mann_whitney_analysis(mw_pairs) -> pd.DataFrame:
    test_results = run_mann_whitney_tests(mw_pairs)
    print("Mann-Whitney tests:")
    print(test_results)
    return test_results


def levene_analysis(levene_pairs) -> pd.DataFrame:
    test_results = run_levene_tests(levene_pairs)
    print("Levene tests:")
    print(test_results)
    return test_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_file", type=str, required=True)
    parser.add_argument("--split_file", type=str, required=True)
    parser.add_argument("--raw_data_file", type=str, required=True)
    args = parser.parse_args()

    mean_ci_and_std_analysis(args)
    print("--------------------------------")
    mw_pairs, levene_pairs = _get_pairs(args)
    mann_whitney_analysis(mw_pairs)
    print("--------------------------------")
    levene_analysis(levene_pairs)


if __name__ == "__main__":
    main()
