import os
import sys

from .app import run, run_api, run_polling
from .logging_config import setup_logging


def main():
    """Главная функция с поддержкой разных режимов запуска"""
    # Инициализация логов до старта
    setup_logging(
        log_dir=os.path.join(os.getcwd(), "logs"),
        level=os.getenv("BOT_LOG_LEVEL", "INFO"),
    )

    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "polling":
            run_polling()
        elif mode == "api":
            host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
            port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
            run_api(host, port)
        else:
            print("Usage: python -m pricescan_bot [polling|api [host] [port]]")
            sys.exit(1)
    else:
        # По умолчанию запускаем API сервер
        run()


if __name__ == "__main__":
    main()
