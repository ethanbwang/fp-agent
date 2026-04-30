import argparse
import time

import pyautogui


def get_mouse_coords(wait_time: float = 3) -> tuple[int, int]:
    """Get the current mouse coordinates."""
    time.sleep(wait_time)
    return pyautogui.position()


def get_rel_coords(
    window_size: tuple[int, int] = (1000, 800), wait_time: float = 3
) -> tuple[int, int]:
    """Get the relative position of the mouse coordinates."""
    screen_size = pyautogui.size()
    window_pos = (
        int(screen_size[0] / 2 - window_size[0] / 2),
        int(screen_size[1] / 2 - window_size[1] / 2),
    )
    abs_coords = get_mouse_coords(wait_time)
    return (abs_coords[0] - window_pos[0], abs_coords[1] - window_pos[1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--wait_time", type=float, default=3)
    parser.add_argument("-x", "--window_size_x", type=int, default=1000)
    parser.add_argument("-y", "--window_size_y", type=int, default=800)
    args = parser.parse_args()

    window_size = (args.window_size_x, args.window_size_y)
    print(get_rel_coords(window_size, args.wait_time))
