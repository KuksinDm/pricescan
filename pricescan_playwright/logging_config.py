import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_dir: str | None = None, level: str | int = "INFO") -> None:
    level_value = getattr(logging, str(level).upper(), logging.INFO)
    fmt = logging.Formatter(LOG_FORMAT, DATE_FMT)

    handlers = [logging.StreamHandler()]
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(
            os.path.join(log_dir, "parser_results.log"),
            maxBytes=10_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        handlers.append(fh)

    root = logging.getLogger()
    root.setLevel(level_value)
    for h in root.handlers[:]:
        root.removeHandler(h)
    for h in handlers:
        h.setFormatter(fmt)
        root.addHandler(h)


def get_results_logger(name: str = "parser_results") -> logging.Logger:
    return logging.getLogger(name)
