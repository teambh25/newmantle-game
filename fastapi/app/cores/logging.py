import datetime
import json
import os
from pathlib import Path

from loguru import logger

EVENTS_DIR = Path("./logs/raw-events")
EVENTS_RETENTION_DAYS = 30


def cleanup_old_events(directory: Path, retention_days: int) -> None:
    """Delete *.jsonl files whose filename date (UTC, first 10 chars) is older than
    retention_days, regardless of PID. Same date axis as the collection DAG.
    Files without a parsable date prefix are kept."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    cutoff = today - datetime.timedelta(days=retention_days)
    for path in directory.glob("*.jsonl"):
        try:
            file_date = datetime.date.fromisoformat(path.name[:10])
        except ValueError:
            continue
        if file_date < cutoff:
            try:
                path.unlink()
            except FileNotFoundError:  # Another worker removed it first
                pass


def _format_event(record: dict) -> str:
    data = {
        "time": record["time"]
        .astimezone(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": record["message"],
        **{k: v for k, v in record["extra"].items() if k != "event"},
    }
    record["extra"]["_json_payload"] = json.dumps(data, ensure_ascii=False)
    return "{extra[_json_payload]}\n"


def setup_logging():
    logger.remove()  # Remove default console handler
    logger.add(
        "./logs/app.log",
        rotation="1 week",
        retention="1 month",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss!UTC} | {level} | {name}:{function}:{line} | {message}",
        filter=lambda record: "event" not in record["extra"],
        colorize=True,
        backtrace=True,
        diagnose=False,
        enqueue=True,
    )
    # One file per worker (PID) so each file has a single writer.
    # No compression: the collection DAG compresses on transfer.
    logger.add(
        f"{EVENTS_DIR}/{{time:YYYY-MM-DD!UTC}}.{os.getpid()}.jsonl",
        rotation="15:00",  # Rotate every KST(UTC+9) midnight
        # loguru passes only the current PID's files; clean the whole directory instead
        retention=lambda _files: cleanup_old_events(EVENTS_DIR, EVENTS_RETENTION_DAYS),
        format=_format_event,
        filter=lambda record: "event" in record["extra"],
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )
