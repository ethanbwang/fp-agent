"""
Script to get data from result files and save to dataset file.

Example usage:

From result files:
python get_data.py --result_files /path/to/result_files --raw_file /path/to/raw_data_file --dataset_file /path/to/dataset_file --split_file /path/to/split_file --check_visitor_id True

From cached raw data:
python get_data.py --raw_file /path/to/raw_data_file --dataset_file /path/to/dataset_file --split_file /path/to/split_file --check_visitor_id True

Note: it is expected to get a bunch of errors with faulty sessions. They will be
excluded from the created dataset.
"""

import argparse
import os

from classifier_training.common import (
    get_dataset,
    get_dataset_split,
    save_dataset_split,
    load_dataset,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result_files",
        type=str,
        help="Path to a result file or directory containing result files. If a directory, will read all result files in the directory.",
    )
    parser.add_argument(
        "--raw_file", type=str, required=True, help="Path to write raw data file"
    )
    parser.add_argument(
        "--dataset_file", type=str, required=True, help="Path to write dataset file"
    )
    parser.add_argument(
        "--split_file", type=str, required=True, help="Path to write split file"
    )
    parser.add_argument(
        "--check_visitor_id",
        type=bool,
        default=False,
        help="Whether to check the visitor id",
    )
    # parser.add_argument(
    #     "--agent_split_file",
    #     type=str,
    #     help="Path to write agent split file",
    # )
    args = parser.parse_args()

    if args.result_files is not None:
        assert os.path.exists(
            args.result_files
        ), f"Result files path {args.result_files} does not exist"

        if os.path.isdir(args.result_files):
            result_files = [
                os.path.join(args.result_files, f)
                for f in os.listdir(args.result_files)
                if f.endswith(".json")
            ]
        else:
            result_files = [args.result_files]

        dataset = get_dataset(
            result_files=result_files,
            output_file=args.dataset_file,
            raw_data_file=args.raw_file,
            overwrite_raw_cache=True,  # Creates new cache, overwriting if raw file path exists
            check_visitor_id=args.check_visitor_id,
        )
    else:
        dataset = get_dataset(
            result_files=[],
            output_file=args.dataset_file,
            raw_data_file=args.raw_file,
            overwrite_raw_cache=False,  # Use existing raw data cache to create dataset
            check_visitor_id=args.check_visitor_id,
        )

    # Split dataset into train and test sets
    split = get_dataset_split(dataset)
    save_dataset_split(*split, args.split_file)

    # Optional, to create dataset containing just browsing agents
    # dataset = load_dataset(args.dataset_file, removed_classes=["Human"])
    # agent_split = get_dataset_split(dataset)
    # save_dataset_split(*agent_split, args.agent_split_file)


if __name__ == "__main__":
    main()
