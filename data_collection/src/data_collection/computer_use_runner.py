from datetime import datetime
import json
import os
import platform

from dotenv import load_dotenv
import requests

from data_collection.desktop_automation import (
    AtlasDesktopWorker,
    ChromeDesktopWorker,
    CometDesktopWorker,
)
from data_collection.universal_runner import TaskRunner

load_dotenv()
WEBSITE_DOMAIN = os.getenv("WEBSITE_DOMAIN")

SYSTEM_NAME = platform.system()
if SYSTEM_NAME == "Windows":
    # Read paths to app installations from app_paths.json
    with open("data_collection/app_paths.json", "r") as f:
        paths = json.load(f)


class AtlasTaskRunner(TaskRunner):
    """Task runner for Atlas tasks."""

    def __init__(
        self,
        task_name: str,
        website_version: str,
        prompt: str,
        save_path: str,
        webpage: str,
        timeout: float = 600,
    ):
        super().__init__(
            task_name,
            "ChatGPT Atlas",
            "Agent mode",
            "N/A",
            "ChatGPT Atlas",
            True,
            website_version,
            prompt,
            save_path,
        )
        self.webpage = webpage
        self.timeout = timeout

    def run_task(self, timeout: float | None = None) -> datetime | None:
        # if timeout is not None:
        #     self.timeout = timeout

        # Send start signal to server
        res = requests.post(
            f"https://{WEBSITE_DOMAIN}/{self.website_version}/start",
            json={"webpage": self.webpage},
        )
        res.raise_for_status()
        assert "X-Exp-Id" in res.headers, "Experiment ID not found in response headers"
        exp_id = int(res.headers["X-Exp-Id"])

        atlas = AtlasDesktopWorker(app_path="", prompt=self.prompt)
        atlas.run()
        self.end_time = atlas.wait_for_end(exp_id)
        return self.end_time


class ChromeTaskRunner(TaskRunner):
    """Task runner for Chrome tasks."""

    def __init__(
        self,
        task_name: str,
        ai_platform: str,
        interface: str,
        llm_model: str,
        website_version: str,
        prompt: str,
        save_path: str,
        agent: str,
        webpage: str,
        timeout: float = 600,
    ):
        super().__init__(
            task_name,
            ai_platform,
            interface,
            llm_model,
            "Google Chrome",
            True,
            website_version,
            prompt,
            save_path,
        )
        self.agent = agent
        self.timeout = timeout
        self.webpage = webpage

    def run_task(self, timeout: float | None = None) -> datetime | None:
        # if timeout is not None:
        #     self.timeout = timeout

        # Send start signal to server
        res = requests.post(
            f"https://{WEBSITE_DOMAIN}/{self.website_version}/start",
            json={"webpage": self.webpage},
        )
        res.raise_for_status()
        assert "X-Exp-Id" in res.headers, "Experiment ID not found in response headers"
        exp_id = int(res.headers["X-Exp-Id"])

        app_path = paths["chrome"] if SYSTEM_NAME == "Windows" else ""
        chrome = ChromeDesktopWorker(app_path=app_path, prompt=self.prompt)
        chrome.run(agent=self.agent)
        self.end_time = chrome.wait_for_end(exp_id)
        return self.end_time


class CometTaskRunner(TaskRunner):
    """Task runner for Comet tasks."""

    def __init__(
        self,
        task_name: str,
        website_version: str,
        prompt: str,
        save_path: str,
        webpage: str,
        timeout: float = 600,
    ):
        super().__init__(
            task_name,
            "Comet",
            "Assistant",
            "N/A",
            "Comet",
            True,
            website_version,
            prompt,
            save_path,
        )
        self.webpage = webpage
        self.timeout = timeout

    def run_task(self, timeout: float | None = None) -> datetime | None:
        # if timeout is not None:
        #     self.timeout = timeout

        # Send start signal to server
        res = requests.post(
            f"https://{WEBSITE_DOMAIN}/{self.website_version}/start",
            json={"webpage": self.webpage},
        )
        res.raise_for_status()
        assert "X-Exp-Id" in res.headers, "Experiment ID not found in response headers"
        exp_id = int(res.headers["X-Exp-Id"])

        app_path = paths["comet"] if SYSTEM_NAME == "Windows" else ""
        comet = CometDesktopWorker(app_path=app_path, prompt=self.prompt)
        comet.run()
        self.end_time = comet.wait_for_end(exp_id)
        return self.end_time
