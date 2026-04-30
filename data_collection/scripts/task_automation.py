import argparse
from dataclasses import dataclass
from itertools import product
import json
import os
import platform
import socket
import subprocess
import time
from typing import Any
import yaml

from dotenv import load_dotenv
import psutil
from tqdm import tqdm

from data_collection.universal_runner import (
    BrowserUseTaskRunner,
    SkyvernTaskRunner,
)
from data_collection.computer_use_runner import ChromeTaskRunner

load_dotenv()
WEBSITE_DOMAIN = os.getenv("WEBSITE_DOMAIN")

SYSTEM_NAME = platform.system()

if SYSTEM_NAME in ["Darwin", "Windows"]:
    from data_collection.computer_use_runner import CometTaskRunner

    if SYSTEM_NAME == "Darwin":
        from data_collection.computer_use_runner import AtlasTaskRunner


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""

    experiment_name: str
    experiment_description: str
    num_trials: int
    task_runner: str
    task_runner_args: dict[str, Any]
    prompt_path: str  # Path to the prompt file
    screen_res: str
    timezone: str | None = None
    dock_position: str | None = None


def start_process(cmd: list[str], **kwargs) -> subprocess.Popen:
    """Start a process."""
    if SYSTEM_NAME == "Windows":
        return subprocess.Popen(
            cmd, **kwargs, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        return subprocess.Popen(cmd, **kwargs, start_new_session=True)


def kill_process_tree(proc: subprocess.Popen, timeout: float = 5) -> None:
    """Kill a process and all its children."""
    try:
        parent = psutil.Process(proc.pid)
    except psutil.NoSuchProcess:
        return

    children = parent.children(recursive=True)

    # Try graceful shutdown
    for child in children:
        child.terminate()

    parent.terminate()

    _, still_alive = psutil.wait_procs(children, timeout=timeout)

    # Force kill if needed
    for p in still_alive:
        p.kill()

    try:
        parent.kill()
    except psutil.NoSuchProcess:
        pass


def parse_experiment_config(config_path: str) -> list[ExperimentConfig]:
    """Parse an experiment configuration file."""
    with open(config_path, "r") as f:
        config = yaml.load(f, yaml.FullLoader)
    experiments = []
    for experiment_config in config["experiments"]:
        for screen_res, timezone in product(config["screen_res"], config["timezone"]):
            experiments.append(
                ExperimentConfig(
                    **(
                        experiment_config
                        | {
                            "screen_res": screen_res,
                            "timezone": timezone,
                        }
                    )
                )
            )
    return experiments


def run_experiment(experiment_config: ExperimentConfig) -> None:
    """Run an experiment."""
    # Read prompt from file
    with open(experiment_config.prompt_path, "r") as f:
        prompt = f.read()
    prompt = prompt.replace(
        "<website_version>", experiment_config.task_runner_args["website_version"]
    )
    if "<domain>" in prompt:
        prompt = prompt.replace("<domain>", WEBSITE_DOMAIN)

    experiment_config.task_runner_args["prompt"] = prompt

    if experiment_config.task_runner == "skyvern":
        # Start Skyvern server
        cmd = ["skyvern", "run", "all"]
        skyvern_proc = start_process(cmd, stdout=None, stderr=None, text=True)

        # Wait for Skyvern server to start
        cur_time = time.time()
        while time.time() - cur_time < 30:
            try:
                socket.create_connection(("127.0.0.1", 8000))
                break
            except ConnectionRefusedError:
                time.sleep(1)
        if time.time() - cur_time >= 30:
            raise TimeoutError("Starting Skyvern server took too long")
    else:
        skyvern_proc = None

    for _ in tqdm(
        range(experiment_config.num_trials),
        desc=f"Running {experiment_config.experiment_name} on {experiment_config.task_runner} with {experiment_config.screen_res} resolution, {experiment_config.timezone} timezone, and {experiment_config.dock_position} taskbar position",
        leave=False,
    ):
        name = f"{experiment_config.task_runner_args['task_name']} - {experiment_config.screen_res} - {experiment_config.timezone} - {experiment_config.dock_position}"
        args = experiment_config.task_runner_args.copy()
        args["task_name"] = name
        task_runner = TASK_RUNNERS[experiment_config.task_runner](**args)
        if task_runner.run_task() is not None:
            task_runner.save_task_details()
        else:
            print(f"Task {name} timed out")

    if skyvern_proc is not None:
        kill_process_tree(skyvern_proc)


TASK_RUNNERS = {
    "browseruse": BrowserUseTaskRunner,
    "chrome": ChromeTaskRunner,
    "skyvern": SkyvernTaskRunner,
}
if SYSTEM_NAME in ["Darwin", "Windows"]:
    TASK_RUNNERS["comet"] = CometTaskRunner

    if SYSTEM_NAME == "Darwin":
        TASK_RUNNERS["atlas"] = AtlasTaskRunner


def main(args):
    experiment_configs = parse_experiment_config(args.config_path)

    if args.skip_existing:
        new_experiment_configs = experiment_configs.copy()
        for experiment_config in experiment_configs:
            if os.path.exists(experiment_config.task_runner_args["save_path"]):
                with open(experiment_config.task_runner_args["save_path"], "r") as f:
                    results = json.load(f)
                name = f"{experiment_config.task_runner_args['task_name']} - {experiment_config.screen_res} - {experiment_config.timezone} - {experiment_config.dock_position}"
                if (
                    results
                    and experiment_config.task_runner_args["website_version"] in results
                ):
                    tasks = results[
                        experiment_config.task_runner_args["website_version"]
                    ]["tasks"]
                    if name in tasks:
                        list = tasks[name]
                        if len(list) >= experiment_config.num_trials:
                            new_experiment_configs.remove(experiment_config)
                        else:
                            experiment_config.num_trials = (
                                experiment_config.num_trials - len(list)
                            )
        experiment_configs = new_experiment_configs

    for experiment_config in tqdm(
        experiment_configs,
        desc=f"Running experiments from {args.config_path}",
    ):
        run_experiment(experiment_config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_path", type=str, required=True)
    parser.add_argument(
        "--skip_existing",
        action="store_true",
        required=False,
        help="Skip experiments that already have results",
    )
    args = parser.parse_args()
    main(args)
