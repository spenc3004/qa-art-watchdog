#!/usr/bin/env python3

import shutil
import sys
import time
import re
from pathlib import Path
import os
import requests
import json

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from db import get_contract_order_detail, insert_art_result


FILENAME_PATTERN = re.compile(r"^(\d+)_(\d+)_(\d+)_.+_(?:unflat|flat)(\d+)\.pdf$")



def get_qa_config() -> tuple[str, str]:
    qa_url = os.getenv("QA_SERVER")
    qa_api_key = os.getenv("QA_API_KEY")

    missing = []
    if not qa_url:
        missing.append("QA_SERVER")
    if not qa_api_key:
        missing.append("QA_API_KEY")

    if missing:
        missing_names = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variable(s): {missing_names}")

    return qa_url, qa_api_key


def parse_file_details(file_name: str) -> tuple[int, int, int, int]:
    match = FILENAME_PATTERN.match(file_name)
    if not match:
        raise ValueError(f"Could not parse file name: {file_name}")

    return tuple(int(value) for value in match.groups())


def serialize_for_json(value):
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def get_qa_report(file_path, in_home_date, no_tagline):
    qa_url, qa_api_key = get_qa_config()
    payload = {
        "pdf_path": str(file_path),
        "input_date": serialize_for_json(in_home_date),
        "noTagline": no_tagline,
    }
    print(f"Sending payload to QA API: {payload}", flush=True)

    response = requests.post(
        qa_url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": qa_api_key,
        }
    )
    response.raise_for_status()
    return response.json()


class FileDropHandler(FileSystemEventHandler):
    def __init__(self, watch_dir: Path) -> None:
        self.backup_dir = watch_dir / "backup"

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)
        if self.backup_dir in path.parents:
            return

        if path.name.startswith("."):
            return

        if not FILENAME_PATTERN.match(path.name):
            return


        try:
            client_id, contract_id, order_line, version = parse_file_details(path.name)
            contract_order = get_contract_order_detail(client_id, contract_id, order_line)
            no_tagline = contract_order["no_tagline"] if contract_order else None
            est_in_home_date = contract_order["est_in_home_date"] if contract_order else None
            print(
                f"no_tagline={no_tagline}, est_in_home_date={est_in_home_date}",
                flush=True,
            )

            result = get_qa_report(path, est_in_home_date, no_tagline)
            print(f"QA Report: {result}", flush=True)
            

            insert_art_result(client_id, contract_id, order_line, version, json.dumps(result))
            print(f"Inserted ART result into database for {client_id}_{contract_id}_{order_line}_v{version}", flush=True)

            self.backup_dir.mkdir(exist_ok=True)
            shutil.move(path, self.backup_dir / path.name)
        except Exception as exc:
            print(f"Failed to process {path.name}: {exc}", flush=True)


def main() -> None:
    watch_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    event_handler = FileDropHandler(watch_dir)
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
