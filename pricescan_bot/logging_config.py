import logging
import logging.handlers
import os


def setup_logging(log_dir: str | None = None, level: str | int = "INFO") -> None:
    """Configure logging for the bot (console + rotating file).

    Idempotent: can be called many times safely.
    """
    if getattr(setup_logging, "_configured", False):
        return

    if isinstance(level, str):
        # В 3.12 использование getLevelName(str) не рекомендуется
        mapping = getattr(logging, "getLevelNamesMapping", None)
        if mapping:
            log_level = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
        else:
            log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        log_level = int(level)

    logger = logging.getLogger()
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File
    if not log_dir:
        log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "bot.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Be quieter for noisy libs if needed
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)

    setup_logging._configured = True  # type: ignore[attr-defined]
