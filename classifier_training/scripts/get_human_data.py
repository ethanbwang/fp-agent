"""
Gets human session start and end points from database and save to JSON file.
Groups requests by visit ID first then uses requests that signify a new session
as a separator.

Usage:
uv run scripts/get_human_data.py --website-version <website_version>
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import timezone
import json
import os
from typing import Any

import dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

from classifier_training.common import get_dataset

dotenv.load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


get_all_data_query = (
    "SELECT * FROM requests WHERE website_version = %s ORDER BY req_ts ASC"
)


def fetch_all(
    query: str, params: list | None = None, dsn: str | None = None, **conn_kwargs
) -> list[dict]:
    """
    Execute a SELECT query and return all rows as a list of dicts.

    Args:
        query (str): SQL query string (use %s placeholders for params).
        params (list | None): Optional list of query parameters.
        dsn (str | None): PostgreSQL database connection string.
        **conn_kwargs: Keyword args passed to psycopg2.connect() if no dsn given
                       e.g. host=, port=, dbname=, user=, password=

    Returns:
        (list[dict]): One dict per row.
    """
    conn = None
    try:
        conn = (
            psycopg2.connect(dsn, **conn_kwargs)
            if dsn
            else psycopg2.connect(**conn_kwargs)
        )
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        if conn:
            conn.close()


def parse_header_text(header_text: str) -> dict[str, str]:
    """Parses header text into a dictionary of headers."""
    header_lines = [line.split(": ") for line in header_text.strip().splitlines()]
    return {x[0]: x[1] for x in header_lines}


# For each visit ID, group into sessions
def is_end_entry(entry: dict, student_website_ver: str) -> bool:
    return (
        entry["endpoint"]
        in [
            f"/{student_website_ver}/end",
            f"/{student_website_ver}/completion",
            f"/{student_website_ver}/complete",
        ]
        # Treat next browser fingerprint request as start of new session
        or entry["endpoint"] == f"/{student_website_ver}/fp"
        and parse_header_text(entry["req_headers"]).get("X-Source") == "result"
    )


def get_entry_task(entry: dict[str, Any]) -> str | None:
    task_names = {"shop": "Shopping", "forums": "Forums", "flights": "Flight-booking"}

    source_page = json.loads(entry["req_body"]).get("sourcePage")
    if source_page is not None:
        for k, v in task_names.items():
            if k in source_page:
                return v
    return None


@dataclass
class Session:
    fp_entry: dict | None
    entries: list[dict]

    def is_valid(self):
        return self.fp_entry is not None and self.entries


def group_into_sessions(entries: list[dict], student_website_ver: str) -> list[Session]:
    """
    Group entries into sessions.

    Assumes entries are grouped by visit ID.
    Separates by end entries.
    """
    sessions = []
    current_session = Session(fp_entry=None, entries=[])
    for entry in entries:
        if is_end_entry(entry, student_website_ver):
            if (
                entry["endpoint"] != f"/{student_website_ver}/fp"
                and current_session.is_valid()
            ):
                current_session.entries.append(entry)
            if current_session.is_valid():
                sessions.append(current_session)

            current_session = Session(fp_entry=None, entries=[])
            if entry["endpoint"] == f"/{student_website_ver}/fp":
                current_session.entries.append(entry)
                current_session.fp_entry = entry
        elif entry["endpoint"] == f"/{student_website_ver}/mm":
            current_session.entries.append(entry)

    if current_session.is_valid():
        sessions.append(current_session)

    return sessions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--website-version", type=str, required=True)
    args = parser.parse_args()
    student_website_ver = args.website_version

    # Fetch all requests with student website version
    all_student_data = fetch_all(
        query=get_all_data_query, params=(student_website_ver,), dsn=DATABASE_URL
    )

    # Group entries by visit ID
    entries_by_visit_id = defaultdict(list)
    for row in all_student_data:
        headers = parse_header_text(row["req_headers"])
        cookies = headers.get("Cookie")
        if cookies:
            try:
                visit_id = cookies.split("visitId=")[1].split(";")[0]
                entries_by_visit_id[visit_id].append(row)
            except:
                continue

    # JSON following result format
    student_results = {
        student_website_ver: {
            "ai_platform": "Human",
            "interface": "N/A",
            "llm_model": "N/A",
            "browser_type": "N/A",
            "headful": True,
            "tasks": defaultdict[str, list](list),
        }
    }

    for visit_id, entries in entries_by_visit_id.items():
        sessions = group_into_sessions(entries, student_website_ver)

        entry_id = 1
        for session in sessions:
            entries = [session.fp_entry] + session.entries
            entries = sorted(entries, key=lambda x: x["req_ts"])
            task = get_entry_task(entries[0])
            headers = parse_header_text(entries[0]["req_headers"])
            cookies = headers.get("Cookie")
            if cookies:
                try:
                    visitor_id = cookies.split("visitorFingerprint=")[1].split(";")[0]
                except:
                    continue

            student_results[student_website_ver]["tasks"][
                f"{task} {visitor_id} {visit_id} entry {entry_id}"
            ].append(
                {
                    "prompt": "N/A",
                    "start_time": entries[0]["req_ts"]
                    .replace(tzinfo=timezone.utc)
                    .isoformat(),
                    "end_time": entries[-1]["req_ts"]
                    .replace(tzinfo=timezone.utc)
                    .isoformat(),
                    "trial_num": entry_id,
                }
            )
            entry_id += 1

    with open("new_student_results.json", "w") as f:
        json.dump(student_results, f)

    # get_dataset(
    #     ["new_student_results.json"],
    #     "data/11-4-2026_human_dataset.json",
    #     "data/11-4-2026_raw_human_dataset.json",
    #     overwrite_raw_cache=True,
    #     check_visitor_id=True,
    # )


if __name__ == "__main__":
    main()
