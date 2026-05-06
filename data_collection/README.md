# Data Collection

This repository contains source code for the task automation used to collect data for FP-Agent.

As the automation is extremely system-dependent, expect to tweak some code (e.g., click coordinates, paths to browsing agent applications). Please contact me if you need any help.

## Requirements

### Dependencies

- Python 3.13 (used 3.12 on Windows)
- [uv](https://docs.astral.sh/uv/)
- [Docker desktop](https://www.docker.com/) (for Skyvern)

### Setup

This repository uses [uv](https://docs.astral.sh/uv/) to manage dependencies.
1. Create virtual environment
    ```bash
    uv init
    ```
2. Install dependencies
    ```bash
    uv sync
    ```
3. Set up Skyvern local server and configure environment variables in generated .env
    ```bash
    skyvern init
    ```
> [!WARNING]
> Skyvern will write over any existing `.env` file in the repository root. Make sure to back up any existing `.env` file.
4. Install Chromium for Browser Use
    ```bash
    uvx browser-use install
    ```
5. **On Windows**: Create a file `app_paths.json`:
    ```json
    {
        "comet": "<path_to_comet>",
        "chrome": "<path_to_chrome>"
    }
    ```

> [!NOTE]
> To get uv to recognize packages, install the module in editable mode using `uv pip install -e .`

### Environment Variables
`DATABASE_URL`: Your database url.

`WEBSITE_DOMAIN`: Domain of honey website.

`LOGGED_USER`: Deprecated, used in [system_control.py](src/data_collection/system_control.py).

## Running 

For Skyvern experiments, make sure to start the local Skyvern database container if using Docker.

1. Create a config file (see [example.yaml](experiments/example_config.yaml))
2. Run the task automation script
    ```bash
    uv run scripts/task_automation.py -c <path_to_config> [--skip_existing]
    ```

> [!NOTE]
> You may need to update the coordinates of the click locations for the GUI automation. Use [get_coords.py](scripts/get_coords.py) to get relative coordinates.

## Results

Results will be in a JSON file mapping website versions to trial metadata + tasks, where tasks maps task name and details to a list of trials.
Data is fetched from the database using filters for website version, start timestamp, and end timestamp.

An example is shown below:
```json
{
    "<website_version>": {
        "ai_platform": "ChatGPT Atlas",
        "interface": "Agent mode",
        "llm_model": "N/A",
        "browser_type": "ChatGPT Atlas",
        "headful": true,
        "tasks": {
            "<task_name> - <timezone> - <screen_res> - None": [
                {
                    "prompt": "<prompt>",
                    "start_time": "<start_timestamp>",
                    "end_time": "<end_timestamp>",
                    "trial_num": 1
                }
            ]
        }
    }
}
```