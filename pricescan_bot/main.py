import os

from .app import run
from .logging_config import setup_logging

if __name__ == "__main__":
    # Инициализация логов до старта
    setup_logging(
        log_dir=os.path.join(os.getcwd(), "logs"),
        level=os.getenv("BOT_LOG_LEVEL", "INFO"),
    )
    run()
