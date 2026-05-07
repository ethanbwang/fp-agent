import argparse

from classifier_training.common import (
    get_dataset,
    get_dataset_split,
    save_dataset_split,
    load_dataset,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_file", type=str, required=True)
    parser.add_argument("--dataset_file", type=str, required=True)
    parser.add_argument("--split_file", type=str, required=True)
    parser.add_argument("--agent_split_file", type=str, required=True)
    args = parser.parse_args()

    dataset = get_dataset(
        result_files=[],
        output_file=args.dataset_file,
        raw_data_file=args.raw_file,
    )

    # Split dataset into train and test sets
    split = get_dataset_split(dataset)
    save_dataset_split(*split, args.split_file)

    # Optional, for dataset containing just browsing agents
    dataset = load_dataset(args.dataset_file, removed_classes=["Human"])
    agent_split = get_dataset_split(dataset)
    save_dataset_split(*agent_split, args.agent_split_file)


if __name__ == "__main__":
    main()
