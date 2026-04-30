import argparse
import random
import string


def generate_random_string(num_strings: int, exclude: list[str] = []) -> list[str]:
    random_size = 10
    new_strings = []
    for _ in range(num_strings):
        new_string = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=random_size)
        )
        while new_string in exclude or new_string in new_strings:
            new_string = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=random_size)
            )
        new_strings.append(new_string)
    return new_strings


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--exclude_file",
        help="Path to file containing line-separated strings to exclude",
    )
    parser.add_argument(
        "-n",
        "--num_strings",
        help="Number of strings to generate",
        type=int,
        required=True,
    )
    args = parser.parse_args()

    if args.exclude_file:
        with open(args.exclude_file, "r") as f:
            exclude = f.readlines()
    else:
        exclude = []

    generated_strings = generate_random_string(args.num_strings, exclude)
    print("\n".join(generated_strings))
