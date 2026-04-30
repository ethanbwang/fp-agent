"""
Desktop automation worker classes for running tasks through computer use.
Only supports MacOS and Windows.
"""

from abc import ABC
from datetime import datetime
import os
import subprocess
import platform
import time

import psycopg2
import pyautogui
import pyperclip
import pywinctl

pyautogui.PAUSE = 0.5
pyautogui.FAILSAFE = True

SYSTEM_NAME = platform.system()


class DesktopWorker(ABC):
    def __init__(self, app_path: str, prompt: str):
        self.app_name = None  # Set by subclass
        self.app_path = app_path
        self.prompt = prompt
        self.screen_size = pyautogui.size()
        self.window_size = (1000, 800)
        self.window_pos = (
            int(self.screen_size[0] / 2 - self.window_size[0] / 2),
            int(self.screen_size[1] / 2 - self.window_size[1] / 2),
        )  # x, y coordinates from left and top

    def _check_if_app_running(self) -> bool:
        """Check if self.app_name is running and has at least one window open."""
        app_windows = pywinctl.getAllAppsWindowsTitles()
        return self.app_name in app_windows and len(app_windows[self.app_name]) > 0

    def _enter_prompt(self) -> None:
        """Enter the prompt into the input box."""
        pyperclip.copy(self.prompt)
        if SYSTEM_NAME == "Darwin":
            pyautogui.hotkey("command", "v", interval=0.1)
        elif SYSTEM_NAME == "Windows":
            pyautogui.hotkey("ctrl", "v", interval=0.1)
        pyautogui.press("enter")

    def _mouse_click(self, coords: tuple[int, int], wait_time: float = 0.25) -> None:
        """Click on a coordinate on the screen."""
        # pyautogui.moveTo(coords[0], coords[1], duration=0.5)
        pyautogui.click(coords[0], coords[1], duration=0.5)
        time.sleep(wait_time)

    def _rel_mouse_click(
        self, coords: tuple[int, int], wait_time: float = 0.25
    ) -> None:
        """Click on a coordinate on the screen relative to the window position."""
        abs_coords = (self.window_pos[0] + coords[0], self.window_pos[1] + coords[1])
        self._mouse_click(abs_coords, wait_time)

    def _resize_and_move_window(self) -> None:
        """Resize and move window to consistent position."""
        window = pywinctl.getActiveWindow()
        if window is not None:
            window.resizeTo(self.window_size[0], self.window_size[1])
            window.moveTo(self.window_pos[0], self.window_pos[1])
        elif SYSTEM_NAME == "Darwin":
            # Try using AppleScript
            script = f"""
            tell application "System Events"
                tell process "{self.app_name}"
                    set position of window 1 to {{{self.window_pos[0]}, {self.window_pos[1]}}}
                    set size of window 1 to {{{self.window_size[0]}, {self.window_size[1]}}}
                end tell
            end tell
            """

            if not self._run_osascript(script):
                raise ValueError(
                    f"Failed to resize and move window for {self.app_name}"
                )

    def _run_osascript(self, script: str) -> bool:
        """Run an AppleScript command. Returns True if successful, False if failed."""
        return subprocess.run(["osascript", "-e", script]).returncode == 0

    def _spotlight_search(self) -> None:
        """
        Search for an app using Spotlight. For MacOS only.

        Since Spotlight does not open a new window if the app is already open,
        manually open a new app window before calling this function.

        Throws an error if the app was unable to be opened or is not found.
        """
        if SYSTEM_NAME != "Darwin":
            raise ValueError(f"Spotlight search is only supported on MacOS.")

        pyautogui.hotkey("command", "space", interval=0.1)
        time.sleep(0.5)
        pyautogui.write(self.app_name)
        pyautogui.press("enter")
        time.sleep(5)  # Wait for app to open
        active_window = pywinctl.getActiveWindow()
        if active_window is None or active_window.getAppName() != self.app_name:
            # Try finding the app window and making it active
            app_windows = pywinctl.getAllWindows()
            for app_window in app_windows:
                if app_window.getAppName() == self.app_name:
                    app_window.activate()
                    return

            # Use AppleScript to activate the app
            script = f'tell application "{self.app_name}" to activate'
            if not self._run_osascript(script):
                raise ValueError(f"Failed to activate {self.app_name}")

    def run(self) -> None:
        raise NotImplementedError

    def wait_for_task_completion(self, timeout: float = 600) -> None:
        """
        Waits for task completion. Defaults to 10 minutes for a conservative
        task duration estimate.
        """
        time.sleep(timeout)
        # Since all apps used are browsers, use cmd + shift + w to close window.
        if SYSTEM_NAME == "Darwin":
            pyautogui.hotkey("command", "shift", "w", interval=0.1)
        elif SYSTEM_NAME in ["Windows", "Linux"]:
            pyautogui.hotkey("ctrl", "shift", "w", interval=0.1)

    def wait_for_end(self, exp_id: int, timeout: float = 900) -> datetime | None:
        cur_time = time.time()
        end_time = None
        db_url = os.getenv("DATABASE_URL")
        if db_url is None:
            raise ValueError("DATABASE_URL is not set in the environment variables.")

        conn = psycopg2.connect(db_url)
        with conn.cursor() as cursor:
            while time.time() - cur_time < timeout:
                cursor.execute(
                    "SELECT end_req FROM experiment_times WHERE exp_id = %s", (exp_id,)
                )
                rows = cursor.fetchone()
                if rows and rows[0] is not None:
                    req_id = rows[0]
                    cursor.execute(
                        "SELECT req_ts FROM requests WHERE req_id = %s", (req_id,)
                    )
                    rows = cursor.fetchone()
                    if rows and rows[0] is not None:
                        end_time = (
                            rows[0]
                            if isinstance(rows[0], datetime)
                            else datetime.fromisoformat(rows[0])
                        )
                    break
                time.sleep(60)  # Wait for 1 minute before checking again
        conn.close()
        time.sleep(10)
        # Since all apps used are browsers, use cmd + shift + w to close window.
        if SYSTEM_NAME == "Darwin":
            pyautogui.hotkey("command", "shift", "w", interval=0.1)
        elif SYSTEM_NAME in ["Windows", "Linux"]:
            pyautogui.hotkey("ctrl", "shift", "w", interval=0.1)
        return end_time


class AtlasDesktopWorker(DesktopWorker):
    def __init__(self, app_path: str, prompt: str):
        super().__init__(app_path, prompt)
        self.app_name = "ChatGPT Atlas"
        # Only works for the (1000, 800) window size
        self.rel_plus_coords = (129, 367)
        self.rel_agent_coords = (92, 483)
        self.rel_input_coords = (184, 365)

    def run(self) -> None:
        running = self._check_if_app_running()
        self._spotlight_search()
        if running:
            # Open a new window
            pyautogui.hotkey("command", "n", interval=0.1)
            time.sleep(5)
        self._resize_and_move_window()

        # Click on plus button
        self._rel_mouse_click(self.rel_plus_coords)

        # Click on agent
        self._rel_mouse_click(self.rel_agent_coords)

        # Click on input
        self._rel_mouse_click(self.rel_input_coords)

        # Enter prompt
        self._enter_prompt()


class ChromeDesktopWorker(DesktopWorker):
    """General desktop worker for any agent that runs through Google Chrome."""

    def __init__(self, app_path: str, prompt: str):
        super().__init__(app_path, prompt)
        self.app_name = "Google Chrome"

        # URLs
        self.chatgpt_url = "https://chatgpt.com"
        self.manus_url = "https://manus.im/app"
        self.mariner_url = "https://labs.google.com/mariner/dashboard"

        # Only works for the (1000, 800) window size
        self.chrome_profile_coords = (599, 543)

        # ChatGPT coordinates
        self.rel_chatgpt_sidebar_coords = (24, 109)
        self.rel_chatgpt_plus_coords = (338, 414)
        self.rel_chatgpt_agent_coords = (382, 611)
        self.rel_chatgpt_input_coords = (402, 413)

        # Manus coordinates
        # self.manus_agent_coords = (678, 477)
        self.rel_manus_sidebar_coords = (24, 115)
        self.rel_manus_input_coords = (383, 400)

        # Claude for Chrome coordinates
        self.rel_claude_extension_coords = (854, 63)
        self.windows_rel_claude_extension_coords = (804, 74)
        self.rel_claude_input_coords = (699, 682)
        self.windows_rel_claude_input_coords = (589, 643)

    def _search_url(self, url: str) -> None:
        """Jump to address bar and enter URL."""
        pyautogui.hotkey("command", "l", interval=0.1)
        time.sleep(0.25)
        pyautogui.write(url, interval=0.02)
        pyautogui.press("enter")
        time.sleep(5)  # Wait for page to load

    def _run_chatgpt(self) -> None:
        self._search_url(self.chatgpt_url)

        # Click on sidebar
        self._rel_mouse_click(self.rel_chatgpt_sidebar_coords)

        # Click on plus button
        self._rel_mouse_click(self.rel_chatgpt_plus_coords)

        # Click on agent
        self._rel_mouse_click(self.rel_chatgpt_agent_coords)

        # Click on input box
        # self._rel_mouse_click(self.rel_chatgpt_input_coords)

        # Enter prompt
        self._enter_prompt()

    def _run_manus(self) -> None:
        self._search_url(self.manus_url)

        # Click on sidebar
        self._rel_mouse_click(self.rel_manus_sidebar_coords)

        # Click on agent
        # self._mouse_click(self.manus_agent_coords)

        # Click on input box
        self._rel_mouse_click(self.rel_manus_input_coords)

        # Enter prompt
        self._enter_prompt()

    def _run_claude(self) -> None:
        if SYSTEM_NAME == "Darwin":
            self._rel_mouse_click(self.rel_claude_extension_coords)
            self._rel_mouse_click(self.rel_claude_input_coords)
        elif SYSTEM_NAME == "Windows":
            self._rel_mouse_click(self.windows_rel_claude_extension_coords)
            self._rel_mouse_click(self.windows_rel_claude_input_coords)

        # Enter prompt
        self._enter_prompt()

    def run(self, agent: str) -> None:
        agent = agent.lower()
        if agent not in ["chatgpt", "manus", "claude"]:
            raise ValueError(f"Invalid agent: {agent}")

        # self._spotlight_search()
        if SYSTEM_NAME == "Darwin":
            os.system(
                f"open -n -a '{self.app_name}' --args --profile-directory='Profile 1'"
            )
        elif SYSTEM_NAME == "Windows":
            cmd = f'"{self.app_path}" --profile-directory="Default" --new-window'
            subprocess.Popen(cmd)

        time.sleep(5)
        self._resize_and_move_window()

        if agent == "chatgpt":
            self._run_chatgpt()
        elif agent == "manus":
            self._run_manus()
        elif agent == "claude":
            self._run_claude()


class CometDesktopWorker(DesktopWorker):

    def __init__(self, app_path: str, prompt: str):
        super().__init__(app_path, prompt)
        self.app_name = "Comet"
        # Only works for the (1000, 800) window size
        self.rel_assistant_coords = (930, 59)
        self.rel_prompt_box_coords = (634, 752)

        self.windows_rel_assistant_coords = (815, 76)
        self.windows_rel_prompt_box_coords = (626, 677)

    def run(self) -> None:
        # self._spotlight_search()
        if SYSTEM_NAME == "Darwin":
            os.system(
                f"open -n -a '{self.app_name}' --args --profile-directory='Default'"
            )
        elif SYSTEM_NAME == "Windows":
            cmd = f'"{self.app_path}" --profile-directory="Default" --new-window'
            subprocess.Popen(cmd)

        time.sleep(5)
        self._resize_and_move_window()

        # Click on assistant
        if SYSTEM_NAME == "Darwin":
            self._rel_mouse_click(self.rel_assistant_coords)
        elif SYSTEM_NAME == "Windows":
            self._rel_mouse_click(self.windows_rel_assistant_coords)

        # Click on prompt box
        if SYSTEM_NAME == "Darwin":
            self._rel_mouse_click(self.rel_prompt_box_coords)
        elif SYSTEM_NAME == "Windows":
            self._rel_mouse_click(self.windows_rel_prompt_box_coords)

        # Enter prompt
        self._enter_prompt()
