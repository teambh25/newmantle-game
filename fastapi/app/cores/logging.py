from loguru import logger


def setup_logging():
    logger.remove()  # Remove default console handler
    logger.add(
        "./logs/app.log",
        rotation="1 week",
        retention="1 month",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss!UTC} | {level} | {message}",
        filter=lambda record: "game" not in record["extra"],
        colorize=True,
        backtrace=False,
        diagnose=True,
        enqueue=True,
    )
    logger.add(
        "./logs/game/{time:YYYY-MM-DD!UTC}.log",
        rotation="15:00",  # Rotate every KST(UTC+9) midnight
        retention="1 month",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss!UTC} | {message}",
        filter=lambda record: "game" in record["extra"],
        enqueue=True,
    )
