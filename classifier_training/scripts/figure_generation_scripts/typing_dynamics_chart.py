import argparse
from dataclasses import dataclass
import json

import matplotlib.pyplot as plt
import numpy as np
import scienceplots

from classifier_training.classifier import TrainingPipeline
from classifier_training.common import summary_stats_1d
from classifier_training.types import FeatureType


@dataclass
class TypingStats:
    interkey_latency_mean: float
    hold_latency_mean: float


MARKER_OFFSET = 0.2

# KEY_LABEL_PAD_PT = 5
KEY_LABEL_PAD_PT = 10

# Colors
hold_latency_color = "#0072B2"  # blue
interkey_latency_color = "#E69F00"  # orange
keydown_color = "#009E73"  # green
keyup_color = "#D55E00"  # red
programmatic_color = "#CC79A7"  # purple


def _key_label_at_marker(
    ax: plt.Axes,
    x: float,
    marker_y: float,
    label: str,
    *,
    side: str,
    fontsize: int = 10,
) -> None:
    # dy = KEY_LABEL_PAD_PT if side == "above" else -KEY_LABEL_PAD_PT
    dy = 4 if side == "above" else -17
    if label == "I":
        dx = 0.4
    elif label == "A":
        dx = 0.4
    elif label == "Del":
        dx = 0.6
    elif label == "Ctrl":
        dx = -0.4
    else:
        dx = 0

    ax.annotate(
        label,
        xy=(x, marker_y),
        xytext=(dx, dy),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=fontsize,
        # usetex=False,  # force non-LaTeX rendering for this label
    )


def plot_typing_dynamics_ones(
    ax: plt.Axes, typing_data: dict[str, TypingStats], arrow_offset: float = 0.15
):
    """
    Plots Atlas Agent, Comet (MacOS), Comet (Windows), Claude (Programmatic), Claude (Typing)
    """
    paste_marker = "$p$"
    change_marker = "$c$"

    for i, (cls, typing_stats) in enumerate(typing_data.items()):
        key1 = "A" if cls == "Claude" else "Ctrl"
        key2 = "I" if cls == "Claude" else "A"
        key3 = "A" if cls == "Claude" else "A"
        key4 = "I" if cls == "Claude" else "Ctrl"
        # Construct timeline
        hl = typing_stats.hold_latency_mean
        ikl = typing_stats.interkey_latency_mean
        t0 = 0
        t1 = t0 + hl
        t2 = t1 + ikl
        t3 = t2 + hl
        if cls == "Comet":
            t2 = t0 + 1.05
            t1 = t3 - 1.05

        # Y position for this class
        y = i
        down_y = i + arrow_offset
        up_y = i - arrow_offset - 0.01

        if cls == "Comet":
            comet_offset = 0.1
            y = i - comet_offset
            down_y = i + arrow_offset - comet_offset
            up_y = i - arrow_offset - comet_offset

        # Plot hold latency (solid line)
        ax.plot(
            [t0, t1] if cls != "Comet" else [t0, t3],
            [y, y],
            color=hold_latency_color,
            linewidth=2,
            label="hold latency" if i == 0 else "",
        )
        ax.plot([t2, t3], [y, y], color=hold_latency_color, linewidth=2)

        # Plot interkey latency (dashed line)
        if cls != "Comet":
            ax.plot(
                [t1, t2],
                [y, y],
                color=interkey_latency_color,
                linestyle="dotted",
                linewidth=2,
                label="inter-key latency" if i == 0 else "",
            )

        # Plot keydown markers
        ax.scatter(
            [t0, t2],
            [down_y, down_y],
            marker="v",
            color=keydown_color,
            label="keydown" if i == 0 else "",
        )

        # Plot keyup markers
        ax.scatter(
            [t1, t3],
            [up_y, up_y],
            marker="^",
            color=keyup_color,
            label="keyup" if i == 0 else "",
        )

        _key_label_at_marker(ax, t0, down_y, key1, side="above")
        _key_label_at_marker(ax, t2, down_y, key2, side="above")
        _key_label_at_marker(ax, t1, up_y, key3, side="below")
        _key_label_at_marker(ax, t3, up_y, key4, side="below")

        if cls == "Comet":
            ax.scatter(
                [t3],
                [down_y],
                marker=paste_marker,
                color=programmatic_color,
                label="paste" if i == 0 else "",
            )
            _key_label_at_marker(ax, t3, down_y, "AI", side="above")

    # Atlas Agent
    atlas_y = 2.9
    ax.scatter(
        [0],
        [atlas_y],
        marker=paste_marker,
        color=programmatic_color,
        label="paste",
    )
    _key_label_at_marker(ax, 0, atlas_y, "AI", side="above")

    # Comet (MacOS)
    comet_y = atlas_y - 0.6
    ax.scatter(
        [0],
        [comet_y],
        marker=paste_marker,
        color=programmatic_color,
        label="paste" if i == 0 else "",
    )
    _key_label_at_marker(ax, 0, comet_y, "AI", side="above")

    # Claude (No Keystrokes)
    claude_nk_y = comet_y - 0.6
    ax.scatter(
        [0],
        [claude_nk_y],
        marker=change_marker,
        color=programmatic_color,
        label="change",
    )
    _key_label_at_marker(ax, 0, claude_nk_y, "AI", side="above")

    # Formatting
    # Set x limits
    ax.set_xlim(-0.3, 3.5)
    ax.set_ylim(-0.7, atlas_y + 0.6)

    # Major ticks (labeled)
    # ax.set_xticks(np.arange(0, 4, 1))
    ax.set_xticks(np.arange(0, 4, 0.5))

    # Minor ticks (unlabeled, high resolution)
    # ax.set_xticks(np.arange(0, 3.01, 0.2), minor=True)
    ax.set_xticks(np.arange(0, 3.51, 0.1), minor=True)

    # Style ticks
    ax.tick_params(axis="x", which="major", length=6)
    ax.tick_params(axis="x", which="minor", length=2)

    # Optional: light grid for readability
    ax.grid(which="major", axis="x", linestyle="-", linewidth=0.5, alpha=0.7)
    ax.grid(which="minor", axis="x", linestyle=":", linewidth=0.5, alpha=0.7)
    ax.tick_params(which="both", right=False, left=False)
    ax.set_yticks([0, 0.9, claude_nk_y, comet_y, atlas_y])
    # ax.set_yticks([0, 0.9, claude_nk_y, atlas_y])

    yticklabels = [
        "Claude$^*$",
        # "Comet (Windows)",
        "Comet$^*$",
        "Claude",
        # "Comet (MacOS)",
        "Comet",
        "Atlas Agent",
    ]
    ax.set_yticklabels(yticklabels)
    # ax.set_ylabel("Class")
    # ax.set_title("Typing Dynamics (2 Keystrokes)")

    # Legend to the right
    # ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))

    # Legend above
    # ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=True)


def plot_typing_dynamics_tens(
    ax: plt.Axes, typing_data: dict[str, TypingStats], arrow_offset: float = 0.125
):
    """
    Plots Browser Use, Skyvern
    """
    key1, key2 = "A", "I"
    for i, (cls, typing_stats) in enumerate(typing_data.items()):
        # Construct timeline
        hl = typing_stats.hold_latency_mean
        ikl = typing_stats.interkey_latency_mean
        t0 = 0
        t1 = t0 + hl
        t2 = t1 + ikl
        t3 = t2 + hl

        # Y position for this class
        y = i
        down_y = i + arrow_offset
        up_y = i - arrow_offset - 0.01

        # Plot hold latency (solid line)
        ax.plot(
            [t0, t1],
            [y, y],
            color=hold_latency_color,
            linewidth=2,
            # label="hold latency" if i == 0 else "",
            label="",
        )
        ax.plot(
            [t2, t3],
            [y, y],
            color=hold_latency_color,
            linewidth=2,
            label="",
        )

        # Plot interkey latency (dashed line)
        ax.plot(
            [t1, t2],
            [y, y],
            color=interkey_latency_color,
            linestyle="dotted",
            linewidth=2,
            # label="interkey latency" if i == 0 else "",
            label="",
        )

        # Plot keydown markers
        ax.scatter(
            [t0, t2],
            [down_y, down_y],
            marker="v",
            color=keydown_color,
            # label="keydown" if i == 0 else "",
            label="",
        )

        # Plot keyup markers

        ax.scatter(
            [t1, t3],
            [up_y, up_y],
            marker="^",
            color=keyup_color,
            # label="keyup" if i == 0 else "",
            label="",
        )

        _key_label_at_marker(ax, t0, down_y, key1, side="above")
        _key_label_at_marker(ax, t2, down_y, key2, side="above")
        _key_label_at_marker(ax, t1, up_y, key1, side="below")
        _key_label_at_marker(ax, t3, up_y, key2, side="below")

    # Formatting
    # Set x limits
    ax.set_xlim(-3, 35)
    ax.set_ylim(-0.75, len(typing_data) - 0.25)

    # Major ticks (labeled)
    ax.set_xticks(np.arange(0, 36, 5))

    # Minor ticks (unlabeled, high resolution)
    ax.set_xticks(np.arange(0, 36, 1), minor=True)

    # Style ticks
    ax.tick_params(axis="x", which="major", length=6)
    ax.tick_params(axis="x", which="minor", length=2)

    # Optional: light grid for readability
    ax.grid(which="major", axis="x", linestyle="-", linewidth=0.5, alpha=0.7)
    ax.grid(which="minor", axis="x", linestyle=":", linewidth=0.5, alpha=0.7)
    ax.tick_params(which="both", right=False, left=False)
    ax.set_yticks(range(len(typing_data)))
    ax.set_yticklabels(typing_data.keys())
    # ax.set_ylabel("Class")
    # ax.set_title("Typing Dynamics (2 Keystrokes)")
    # ax.legend()


def plot_typing_dynamics_hundreds(
    ax: plt.Axes, typing_data: dict[str, TypingStats], arrow_offset: float = 0.135
):
    """
    Plots Human, Manus, ChatGPT Agent
    """
    for i, (cls, typing_stats) in enumerate(typing_data.items()):
        if cls == "Human":
            key1 = "A"
            key2 = "I"
            key3 = "A"
            key4 = "I"
        elif cls == "ChatGPT Agent":
            key1 = "Ctrl"
            key2 = "V"
            key3 = "V"
            key4 = "Ctrl"
        elif cls == "Manus":
            key1 = "Del"
            key2 = "A"
            key3 = "Del"
            key4 = "A"
            key5 = "I"
            key6 = "I"

        # Construct timeline
        hl = typing_stats.hold_latency_mean
        ikl = typing_stats.interkey_latency_mean
        t0 = 0
        t1 = t0 + hl
        t2 = t1 + ikl
        t3 = t2 + hl
        if cls == "ChatGPT Agent":
            t2 = t0 + 31.9
            t1 = t3 - 31.9
        elif cls == "Manus":
            t4 = t3 + ikl
            t5 = t4 + hl

        # Y position for this class
        y = i
        down_y = i + arrow_offset
        up_y = i - arrow_offset - 0.01

        # Plot hold latency (solid line)
        ax.plot(
            [t0, t1] if cls != "ChatGPT Agent" else [t0, t3],
            [y, y],
            color=hold_latency_color,
            linewidth=2,
            # label="hold latency" if i == 0 else "",
            label="",
        )
        ax.plot(
            [t2, t3],
            [y, y],
            color=hold_latency_color,
            linewidth=2,
            label="",
        )

        if cls == "Manus":
            ax.plot(
                [t4, t5],
                [y, y],
                color=hold_latency_color,
                linewidth=2,
                label="",
            )

        # Plot interkey latency (dashed line)
        if cls != "ChatGPT Agent":
            ax.plot(
                [t1, t2],
                [y, y],
                color=interkey_latency_color,
                linestyle="dotted",
                linewidth=2,
                # label="interkey latency" if i == 0 else "",
                label="",
            )
        if cls == "Manus":
            ax.plot(
                [t3, t4],
                [y, y],
                color=interkey_latency_color,
                linestyle="dotted",
                linewidth=2,
                # label="interkey latency" if i == 0 else "",
                label="",
            )

        # Plot keydown / keyup markers
        keydown_ts = [t0, t2]
        keyup_ts = [t1, t3]
        if cls == "Manus":
            keydown_ts.append(t4)
            keyup_ts.append(t5)
        ax.scatter(
            keydown_ts,
            [down_y for _ in range(len(keydown_ts))],
            marker="v",
            color=keydown_color,
            # label="keydown" if i == 0 else "",
            label="",
        )
        ax.scatter(
            keyup_ts,
            [up_y for _ in range(len(keyup_ts))],
            marker="^",
            color=keyup_color,
            # label="keyup" if i == 0 else "",
            label="",
        )

        _key_label_at_marker(ax, t0, down_y, key1, side="above")
        _key_label_at_marker(ax, t2, down_y, key2, side="above")
        _key_label_at_marker(ax, t1, up_y, key3, side="below")
        _key_label_at_marker(ax, t3, up_y, key4, side="below")
        if cls == "ChatGPT Agent":
            paste_ts = (t2 - t1) / 2 + t1
            ax.scatter(
                [paste_ts],
                [down_y],
                marker="$p$",
                color=programmatic_color,
                # label="paste" if i == 0 else "",
            )
            _key_label_at_marker(ax, paste_ts, down_y, "AI", side="above")
        elif cls == "Manus":
            _key_label_at_marker(ax, t4, down_y, key5, side="above")
            _key_label_at_marker(ax, t5, up_y, key6, side="below")

    # Formatting
    # Set x limits
    ax.set_xlim(-25, 350)
    ax.set_ylim(-0.75, len(typing_data) - 0.25)

    # Major ticks (labeled)
    ax.set_xticks(np.arange(0, 351, 50))

    # Minor ticks (unlabeled, high resolution)
    ax.set_xticks(np.arange(0, 351, 10), minor=True)

    # Style ticks
    ax.tick_params(axis="x", which="major", length=6)
    ax.tick_params(axis="x", which="minor", length=2)

    # Optional: light grid for readability
    ax.grid(which="major", axis="x", linestyle="-", linewidth=0.5, alpha=0.7)
    ax.grid(which="minor", axis="x", linestyle=":", linewidth=0.5, alpha=0.7)
    ax.tick_params(which="both", right=False, left=False)
    ax.set_yticks(range(len(typing_data)))
    ax.set_yticklabels(typing_data.keys())
    ax.set_xlabel("Time (ms)")
    # ax.set_ylabel("Class")
    # ax.set_title("Typing Dynamics (2 Keystrokes)")
    # ax.legend()


def plot_typing_dynamics(agent_typing_data, fig_size: tuple[float, float] = (3.5, 7)):
    """
    data: dict mapping class_name -> (interkey_latency, hold_latency)
    Example:
        {
            "A": (50, 100),
            "B": (30, 80),
        }
    """
    nrows = 3
    ncols = 1

    ones_data = {}
    for agent in ["Claude", "Comet"]:
        ones_data[agent] = agent_typing_data[agent]
    tens_data = {}
    for agent in ["Browser Use", "Skyvern"]:
        tens_data[agent] = agent_typing_data[agent]
    hundkeyup_colors_data = {}
    for agent in ["Human", "Manus", "ChatGPT Agent"]:
        hundkeyup_colors_data[agent] = agent_typing_data[agent]

    with plt.style.context("science"):
        with plt.rc_context({"font.size": 10}):
            fig, axes = plt.subplots(
                nrows=nrows,
                ncols=ncols,
                figsize=fig_size,
                gridspec_kw={"height_ratios": [5, 3.5, 4.75]},
                constrained_layout=True,
            )
            axes = axes.flatten()

            plot_typing_dynamics_ones(axes[0], ones_data)
            plot_typing_dynamics_tens(axes[1], tens_data)
            plot_typing_dynamics_hundreds(axes[2], hundkeyup_colors_data)

            for ax in axes:
                ax.set_aspect("auto")

            # fig.subplots_adjust(left=0.1, right=0.90, top=0.88, bottom=0)
            fig.legend(
                loc="lower center",
                bbox_to_anchor=(0.5, 1),
                ncol=3,
                frameon=True,
                columnspacing=1.0,  # space between columns (default 2.0)
            )

            # plt.show()
            return fig


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

    # Get typing latencies for each agent
    agent_stats = pipeline.get_agent_feature_stats(
        FeatureType.BEHAVIORAL,
        {
            "interkey_latency_mean": None,
            "hold_latency_mean": None,
            "interkey_latency_median": None,
            "hold_latency_median": None,
            "interkey_latency_stdev": None,
            "hold_latency_stdev": None,
        },
    )

    latencies = {}
    for agent, stats in agent_stats.items():
        latencies[agent] = TypingStats(
            interkey_latency_mean=stats["interkey_latency_mean"]["mean"],
            hold_latency_mean=stats["hold_latency_mean"]["mean"],
        )

    # Since Claude types on the Forums task, calculate typing latencies on those samples
    claude_stats = pipeline.get_agent_feature_stats(
        FeatureType.BEHAVIORAL,
        {
            "interkey_latency_mean": None,
            "hold_latency_mean": None,
            "interkey_latency_median": None,
            "hold_latency_median": None,
            "interkey_latency_stdev": None,
            "hold_latency_stdev": None,
        },
        tasks=["Forums"],
    )["Claude"]

    latencies["Claude"] = TypingStats(
        claude_stats["interkey_latency_mean"]["mean"],
        claude_stats["hold_latency_mean"]["mean"],
    )

    # Get Comet Ctrl+A keypress latencies on Windows
    windows_comet_data = []
    for source, vecs in pipeline.dataset.data["Comet"].items():
        source_json = json.loads(source)
        if source_json["website_version"] == "AGJX7Y80OL":
            windows_comet_data.append(vecs["behavioral"])

    comet_stats = {
        "interkey_latency_mean": [],
        "interkey_latency_median": [],
        "interkey_latency_range": [],
        "interkey_latency_stdev": [],
        "hold_latency_mean": [],
        "hold_latency_median": [],
        "hold_latency_range": [],
        "hold_latency_stdev": [],
    }

    for behavioral_fv in windows_comet_data:
        comet_stats["interkey_latency_mean"].append(behavioral_fv[35])
        comet_stats["interkey_latency_median"].append(behavioral_fv[36])
        comet_stats["interkey_latency_range"].append(behavioral_fv[37])
        comet_stats["interkey_latency_stdev"].append(behavioral_fv[38])
        comet_stats["hold_latency_mean"].append(behavioral_fv[39])
        comet_stats["hold_latency_median"].append(behavioral_fv[40])
        comet_stats["hold_latency_range"].append(behavioral_fv[41])
        comet_stats["hold_latency_stdev"].append(behavioral_fv[42])

    for key, vals in comet_stats.items():
        comet_stats[key] = summary_stats_1d(vals)

    # Keyboard shortcuts don't produce inter-key statistics
    latencies["Comet"] = TypingStats(0, comet_stats["hold_latency_mean"]["mean"])
    latencies["ChatGPT Agent"].interkey_latency_mean = 0

    fig = plot_typing_dynamics(latencies)
    fig.savefig(args.out_file, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
