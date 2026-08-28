import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import scienceplots

COLORS = [
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # green
    "#D55E00",  # red
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot F1 score against k for four CSV files."
    )
    parser.add_argument(
        "csv_files",
        nargs=4,
        type=Path,
        metavar="CSV",
        help="Four CSV files containing 'k' and 'F1' columns",
    )
    parser.add_argument(
        "--x_range",
        type=int,
        help="Maximum number of interactions",
    )
    parser.add_argument(
        "--output_file",
        type=Path,
        metavar="OUTPUT",
        help="Path where the graph will be saved (for example, graph.png)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with plt.style.context(["science"]):
        fig, ax = plt.subplots(figsize=(3.33, 2))

        for csv_file, color in zip(args.csv_files, COLORS):
            data = pd.read_csv(csv_file)
            missing_columns = {"k", "F1"} - set(data.columns)
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise ValueError(f"{csv_file} is missing required column(s): {missing}")

            ax.plot(
                data["k"][: args.x_range],
                data["F1"][: args.x_range],
                label=csv_file.stem.split("_")[0].capitalize(),
                color=color,
            )

        ax.set_xticks(range(0, args.x_range + 1, 50))
        ax.set_xticks(range(0, args.x_range + 1, 10), minor=True)
        ax.set_xlabel("Number of Interactions")
        ax.set_ylabel("$F_1$ Score")
        # ax.set_title("F1 vs. Number of Interactions")
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
        ax.grid(alpha=0.3)

        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(args.output_file, dpi=300, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    main()
