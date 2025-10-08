import logging
import logging.handlers
import os


def setup_logging(log_dir: str | None = None, level: str | int = "INFO") -> None:
    if getattr(setup_logging, "_configured", False):
        return

    if isinstance(level, str):
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

    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if not log_dir:
        log_dir = os.path.join(os.getcwd(), "logs", "bot")  # Отдельная папка для бота
    os.makedirs(log_dir, exist_ok=True)

    main_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "bot.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    main_handler.setLevel(log_level)
    main_handler.setFormatter(formatter)
    logger.addHandler(main_handler)

    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "bot_errors.log"),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    user_actions_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "bot_user_actions.log"),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding="utf-8",
    )
    user_actions_handler.setLevel(logging.INFO)
    user_actions_handler.setFormatter(formatter)

    user_logger = logging.getLogger("user_actions")
    user_logger.addHandler(user_actions_handler)
    user_logger.setLevel(logging.INFO)
    user_logger.propagate = False

    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    setup_logging._configured = True


def get_user_actions_logger() -> logging.Logger:
    return logging.getLogger("user_actions")
