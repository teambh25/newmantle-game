import json

from loguru import logger


def _format_event(record: dict) -> str:
    data = {
        "time": record["time"].strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    logger.add(
        "./logs/events/{time:YYYY-MM-DD!UTC}.jsonl",
        rotation="15:00",  # Rotate every KST(UTC+9) midnight
        retention="1 month",
        format=_format_event,
        filter=lambda record: "event" in record["extra"],
        compression="zip",
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )
