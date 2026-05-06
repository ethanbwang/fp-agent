from abc import ABC
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from browser_use import Agent, ChatOpenAI, ChatAnthropic
from dotenv import load_dotenv
from skyvern import Skyvern
from skyvern.client import SkyvernEnvironment
from skyvern.schemas.runs import RunEngine, RunStatus
import requests

load_dotenv()
WEBSITE_DOMAIN = os.getenv("WEBSITE_DOMAIN")


class TaskRunner(ABC):
    """Abstract base class wrapping task data and end-to-end functionality for running tasks."""

    def __init__(
        self,
        task_name: str,
        ai_platform: str,
        interface: str,
        llm_model: str,
        browser_type: str,
        headful: bool,
        website_version: str,
        prompt: str,
        save_path: str,
    ):
        """
        Args:
            task_name: The name of the task.
            ai_platform: The AI platform being used.
            interface: The platform interface being used.
            llm_model: The LLM model being used.
            browser_type: The browser type being used.
            headful: Whether the browser is running in headful mode.
            website_version: Website version being used.
            prompt: Task prompt.
            save_path: Save path for task details.
        """
        self.task_name = task_name
        self.ai_platform = ai_platform
        self.interface = interface
        self.llm_model = llm_model
        self.browser_type = browser_type
        self.headful = headful
        self.website_version = website_version
        self.prompt = prompt
        self.save_path = save_path

        # Use start and end times to get request data from database
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None

    def run_task(self, prompt: str | None = None) -> None:
        raise NotImplementedError

    def save_task_details(self, save_path: str | None = None) -> None:
        """Saves task details as a JSON file."""
        if save_path is not None:
            self.save_path = save_path

        trial_details = {
            "prompt": self.prompt,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }

        # Create file if it doesn't exist
        if not os.path.exists(self.save_path):
            path = Path(self.save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

            with open(self.save_path, "w") as f:
                json.dump({}, f)

        with open(self.save_path, "r+") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                # Empty file
                existing_data = {}

            if self.website_version not in existing_data:
                existing_data[self.website_version] = {
                    "ai_platform": self.ai_platform,
                    "interface": self.interface,
                    "llm_model": self.llm_model,
                    "browser_type": self.browser_type,
                    "headful": self.headful,
                    "tasks": {},
                }

            tasks_list = existing_data[self.website_version]["tasks"]
            if self.task_name not in tasks_list:
                tasks_list[self.task_name] = []

            # Set trial number
            if len(tasks_list[self.task_name]) == 0:
                # First trial
                trial_details["trial_num"] = 1
            else:
                # One more than the highest trial number
                trial_details["trial_num"] = (
                    max(trial["trial_num"] for trial in tasks_list[self.task_name]) + 1
                )

            # Write trial details to file
            tasks_list[self.task_name].append(trial_details)
            f.seek(0)
            json.dump(existing_data, f)
            f.truncate()


class BrowserUseTaskRunner(TaskRunner):
    """Task runner for Browser Use tasks."""

    # Static mapping of LLM models to ChatOpenAI and ChatAnthropic classes
    LLM_MODELS = {
        "gpt-5": ChatOpenAI,
        "gpt-5-mini": ChatOpenAI,
        "computer-use-preview": ChatOpenAI,
        "claude-3.5-sonnet": ChatAnthropic,
        "claude-sonnet-4-0": ChatAnthropic,
    }

    def __init__(
        self,
        task_name: str,
        interface: str,
        llm_model: str,
        browser_type: str,
        headful: bool,
        website_version: str,
        prompt: str,
        save_path: str,
    ):
        super().__init__(
            task_name,
            "Browser Use",
            interface,
            llm_model,
            browser_type,
            headful,
            website_version,
            prompt,
            save_path,
        )

    def run_task(
        self, prompt: str | None = None, max_steps: int = 30
    ) -> datetime | None:
        if prompt is not None:
            self.prompt = prompt

        agent = Agent(
            task=self.prompt,
            llm=self.LLM_MODELS[self.llm_model](model=self.llm_model),
        )
        agent.run_sync(max_steps=max_steps)
        self.end_time = datetime.now(timezone.utc)
        return self.end_time


class SkyvernTaskRunner(TaskRunner):
    """
    Task runner for Skyvern tasks. Make sure that Skyvern local server is
    running before running the task (`skyvern run all`).

    Note: To start Skyvern server, the database Docker container must be running.
    """

    def __init__(
        self,
        task_name: str,
        interface: str,
        llm_model: str,
        browser_type: str,
        headful: bool,
        website_version: str,
        prompt: str,
        save_path: str,
        website_url: str,
        browser_path: str | None = None,
        url: str | None = None,
        engine: RunEngine = RunEngine.skyvern_v1,
    ):
        """
        Args:
            task_name: The name of the task.
            interface: The platform interface being used.
            llm_model: The LLM model being used.
            browser_type: Vendor of browser or cloud browser.
            headful: Whether the browser is running in headful mode.
            website_version: Website version being used.
            prompt: Task prompt.
            save_path: Save path for task details.
            browser_path: Path to the browser to use.
            url: URL of the website to run the task on.
            engine: Skyvern engine to use.
        """
        super().__init__(
            task_name,
            "Skyvern",
            interface,
            llm_model,
            browser_type,
            headful,
            website_version,
            prompt,
            save_path,
        )
        self.browser_path = browser_path
        self.url = url
        self.engine = engine
        if "<domain>" in website_url:
            website_url = website_url.replace("<domain>", WEBSITE_DOMAIN)
        self.website_url = website_url

    def run_task(
        self, prompt: str | None = None, max_steps: int = 15
    ) -> datetime | None:
        if prompt is not None:
            self.prompt = prompt

        # Just send a POST request to Skyvern API endpoint.
        response = requests.post(
            url="http://localhost:8000/api/v1/tasks",
            headers={
                "Content-Type": "application/json",
                "x-api-key": os.getenv("SKYVERN_API_KEY"),
                "x-max-steps-override": str(max_steps),
                "x-user-agent": "skyvern-ui",
            },
            data=json.dumps(
                {
                    "title": self.task_name,
                    "url": self.website_url,
                    "webhook_callback_url": None,
                    "navigation_goal": self.prompt,
                    "data_extraction_goal": None,
                    "proxy_location": "RESIDENTIAL",
                    "navigation_payload": "null",
                    "extracted_information_schema": None,
                    "totp_identifier": None,
                    "error_code_mapping": None,
                }
            ),
        )
        response.raise_for_status()
        run_id = response.json()["task_id"]
        skyvern = Skyvern(environment=SkyvernEnvironment.LOCAL)
        while True:
            time.sleep(60)
            run = asyncio.run(skyvern.get_run(run_id))
            if RunStatus(run.status).is_final():
                if RunStatus(run.status) != RunStatus.completed:
                    raise RuntimeError(f"Skyvern task failed with status {run.status}")
                break
        self.end_time = datetime.now(timezone.utc)
        return self.end_time
