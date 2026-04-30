"""
Originally used to change taskbar position, screen resolution, and timezone.
Ended up not using it for experiments.
"""

from dataclasses import dataclass
import os
import platform
import subprocess

from dotenv import load_dotenv

load_dotenv()
USER = os.getenv("LOGGED_USER")

# Darwin, Linux, Windows
OS_NAME = platform.system()

TIMEZONES = {
    "Darwin": {
        "chicago": "America/Chicago",
        "los angeles": "America/Los_Angeles",
        "new york": "America/New_York",
        "calcutta": "Asia/Calcutta",
        "london": "Europe/London",
    },
    "Linux": {
        "chicago": "America/Chicago",
        "los angeles": "America/Los_Angeles",
        "new york": "America/New_York",
        "calcutta": "Asia/Kolkata",
        "london": "Europe/London",
    },
    "Windows": {
        "chicago": "Central Standard Time",
        "los angeles": "Pacific Standard Time",
        "new york": "Eastern Standard Time",
        "calcutta": "India Standard Time",
        "london": "GMT Standard Time",
    },
}

RESOLUTIONS = {
    "Darwin": {
        "1080p": "1920x1080",
        "2160p": "3840x2160",
    },
    "Linux": {
        "1080p": "1920x1080",
    },
}


@dataclass
class ScreenResolution:
    """Resolution class."""

    width: int
    height: int


def get_timezone_name() -> str:
    """
    Get current timezone name.
    """
    if OS_NAME == "Windows":
        # Returns something like "Pacific Standard Time"
        out = subprocess.check_output(["tzutil", "/g"], text=True)
        return out.strip()

    elif OS_NAME == "Darwin":
        try:
            out = subprocess.check_output(
                ["systemsetup", "-gettimezone"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            # "Time Zone: America/Los_Angeles"
            return out.split(":", 1)[1].strip()
        except Exception:
            # Fallback: /etc/localtime symlink
            try:
                tz_path = os.path.realpath("/etc/localtime")
                # .../zoneinfo/Region/City
                parts = tz_path.split("zoneinfo/")
                if len(parts) == 2:
                    return parts[1]
            except Exception:
                pass
            raise RuntimeError("Could not determine timezone on macOS")

    elif OS_NAME == "Linux":
        # Preferred: timedatectl (systemd)
        try:
            out = subprocess.check_output(
                ["timedatectl", "show", "-p", "Timezone", "--value"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            return out.strip()
        except Exception:
            # Fallback: /etc/localtime symlink
            try:
                tz_path = os.path.realpath("/etc/localtime")
                parts = tz_path.split("zoneinfo/")
                if len(parts) == 2:
                    return parts[1]
            except Exception:
                pass
            raise RuntimeError("Could not determine timezone on Linux")

    else:
        raise NotImplementedError(f"Unsupported OS: {OS_NAME}")


def set_timezone(tz_name: str) -> None:
    """
    Set system timezone.

    Args:
        tz_name: The name of the timezone to set.
    """
    if OS_NAME == "Darwin":
        # e.g. "America/Los_Angeles"
        cmd = ["systemsetup", "-settimezone", tz_name]
    elif OS_NAME == "Linux":
        # systemd-style; most modern distros
        cmd = ["sudo", "timedatectl", "set-timezone", tz_name]
    elif OS_NAME == "Windows":
        # tz_name must be a Windows time zone ID
        cmd = ["tzutil", "/s", tz_name]
    else:
        raise ValueError(f"Timezone change not implemented for OS {OS_NAME}")

    subprocess.run(cmd, check=True)


def get_screen_resolution(screen_id: str | None = None) -> ScreenResolution:
    """
    Get current screen resolution.
    """
    if OS_NAME == "Windows":
        # Uses Win32 GetSystemMetrics
        import ctypes

        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()  # avoid scaling lies
        w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return ScreenResolution(w, h)

    elif OS_NAME == "Darwin":
        proc = subprocess.run(
            ["displayplacer", "list"], capture_output=True, check=True
        )
        output = proc.stdout.decode("utf-8").strip()
        line = output.splitlines()[-1].replace("displayplacer ", "")
        screens = line.strip('"').split('" "')
        if screen_id is None:
            # Get leftmost screen
            screen = screens[0]
        else:
            for screen_str in screens:
                if screen_id in screen_str:
                    screen = screen_str
                    break
            else:
                raise ValueError(f"Screen ID {screen_id} not found")

        res = screen.split("res:")[1].split(" ")[0].strip()
        w, h = res.split("x")
        return ScreenResolution(int(w), int(h))

    elif OS_NAME == "Linux":
        # X11/Xvfb: parse xrandr
        # Works fine under Xvfb as long as DISPLAY is set
        out = subprocess.check_output(["xrandr"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Screen 0:"):
                # e.g. "Screen 0: minimum 1 x 1, current 1920 x 1080, maximum 32767 x 32767"
                parts = line.split(",")
                for p in parts:
                    p = p.strip()
                    if p.startswith("current "):
                        _, dims = p.split("current ", 1)
                        w_str, h_str = dims.split(" x ")
                        return ScreenResolution(int(w_str), int(h_str))
        raise RuntimeError("Could not parse xrandr output for resolution")

    else:
        raise NotImplementedError(f"Unsupported OS: {OS_NAME}")


def set_resolution(resolution: ScreenResolution, screen_id: str | None = None) -> None:
    """
    Set system resolution.

    Args:
        resolution: The resolution to set.
    """
    if OS_NAME == "Darwin":
        if screen_id is None:
            # Get leftmost screen's ID
            proc = subprocess.run(
                ["displayplacer", "list"], capture_output=True, check=True
            )
            output = proc.stdout.decode("utf-8")
            for line in output.splitlines():
                if "Persistent screen id" in line:
                    screen_id = line.split(": ")[1].strip()
                    break

        cmd = [
            "displayplacer",
            f"id:{screen_id} res:{resolution.width}x{resolution.height} scaling:on",
        ]
    # elif OS_NAME == "Linux":
    #     if not opts.linux_output:
    #         raise ValueError(
    #             "On Linux (X11) you must provide opts.linux_output "
    #             "(run `xrandr` to see available outputs, e.g. HDMI-1)."
    #         )
    #     # xrandr --output HDMI-1 --mode 1920x1080
    #     mode = f"{width}x{height}"
    #     cmd = ["xrandr", "--output", opts.linux_output, "--mode", mode]
    #     subprocess.run(cmd, check=True)
    # elif OS_NAME == "Windows":
    #     cmd = ["xrandr", "--output", "HDMI-1", "--mode", f"{width}x{height}"]
    else:
        raise ValueError(f"Resolution change not implemented for OS {OS_NAME}")

    subprocess.run(cmd, check=True)


def get_taskbar_position() -> str:
    """
    Get current taskbar position.
    """
    if OS_NAME == "Darwin":
        out = subprocess.check_output(
            [
                "sudo",
                "-u",
                USER,
                "defaults",
                "read",
                "com.apple.dock",
                "orientation",
            ],
            text=True,
        )
        return out.strip()

    elif OS_NAME == "Windows":
        # There is NO supported public API for this.
        # Most solutions read Explorer's "StuckRects3" registry blob,
        # which is undocumented and version-dependent.
        #
        # I'll show a best-effort hack, but treat this as fragile.
        import winreg

        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                data, _ = winreg.QueryValueEx(key, "Settings")
            # data is a bytes object; byte at index 12 encodes position on Win10:
            # 0x00 = left, 0x01 = top, 0x02 = right, 0x03 = bottom
            pos_byte = data[12]
            mapping = {0: "left", 1: "top", 2: "right", 3: "bottom"}
            return mapping.get(pos_byte, f"unknown({pos_byte})")
        except Exception:
            raise RuntimeError(
                "Could not read Windows taskbar position; "
                "this is undocumented and OS-version dependent."
            )

    elif OS_NAME == "Linux":
        # No generic concept of "taskbar".
        # Each desktop environment (GNOME, KDE, XFCE, etc.) has its own config.
        # Example (GNOME with dash-to-dock extension):
        #   gsettings get org.gnome.shell.extensions.dash-to-dock dock-position
        raise NotImplementedError(
            "Dock/taskbar position on Linux is DE-specific; "
            "you must handle GNOME/KDE/etc separately."
        )

    else:
        raise NotImplementedError(f"Unsupported OS: {OS_NAME}")


def set_taskbar_position(position: str) -> None:
    """
    Set taskbar position.

    position: 'left', 'right', 'bottom', maybe 'top' (Windows/Linux only conceptually).

    macOS: implemented via Dock orientation.
    Windows / Linux: left as stubs because it's OS-version/DE-specific and fragile.
    """
    position = position.lower()
    if OS_NAME == "Darwin":
        if position not in {"left", "right", "bottom"}:
            raise ValueError("macOS Dock supports 'left', 'right', or 'bottom'")
        # defaults write com.apple.dock orientation -string "left"; killall Dock
        subprocess.run(
            [
                "sudo",
                "-u",
                USER,
                "defaults",
                "write",
                "com.apple.dock",
                "orientation",
                "-string",
                position,
            ],
            check=True,
        )
        subprocess.run(["killall", "Dock"], check=True)

    elif OS_NAME == "Windows":
        # You *can* do this with registry hacks that vary between Win10/11
        # and may break with updates. Keeping this explicit so you decide.
        raise ValueError(
            "Taskbar position automation on Windows is registry- and version-specific. "
            "Implement only if you're comfortable with brittle hacks."
        )

    elif OS_NAME == "Linux":
        # DE-specific (GNOME, KDE, XFCE, etc.), different config each time.
        raise ValueError(
            "Dock/panel position on Linux is desktop-environment-specific. "
            "Use e.g. gsettings for GNOME or Plasma config tools for KDE."
        )

    else:
        raise ValueError(f"Dock/taskbar position not implemented for OS {OS_NAME}")
