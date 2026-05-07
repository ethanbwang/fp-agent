from typing import Any

EXPECTED_LENGTHS = {
    "p": 4,
    "i": 5,
    "mm": 5,
    "md": 6,
    "mu": 6,
    "kd": 5,
    "ku": 5,
    "sc": 5,
    "se": 5,
    "c": 5,
}


def preprocess_tuple(data_tuple: tuple[Any, ...]) -> tuple[Any, ...]:
    """
    Preprocesses a data tuple by adding "N/A" at index 1 if the tuple
    is one element shorter than the expected length.

    Args:
        data_tuple: The data tuple to preprocess
        expected_length: The expected length of the tuple

    Returns:
        The preprocessed tuple with "N/A" inserted at index 1 if needed,
        otherwise returns the original tuple unchanged.
    """
    current_length = len(data_tuple)
    event_type = data_tuple[0]
    assert event_type in EXPECTED_LENGTHS, f"Invalid event type: {event_type}"

    expected_length = EXPECTED_LENGTHS[event_type]
    if event_type in ["kd", "ku"] and current_length == 3:
        return tuple([data_tuple[0], "N/A", data_tuple[1], False, data_tuple[2]])
    elif event_type == "c" and current_length == 3:
        expected_length = 4

    if current_length == expected_length - 1:
        # Convert tuple to list to allow insertion
        data_list = list(data_tuple)
        data_list.insert(1, "N/A")
        return tuple(data_list)

    return data_tuple
