import logging
import logging.handlers
import os


def setup_logging(log_dir: str | None = None, level: str | int = "INFO") -> None:
    """Настройка логирования для BeautifulSoup парсера
    с отдельными файлами для разных типов логов.

    Идемпотентная функция: можно вызывать многократно без проблем.
    """
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

    # Консольный вывод
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Настройка файлового логирования
    if not log_dir:
        log_dir = os.path.join(
            os.getcwd(), "logs", "parser"
        )  # Отдельная папка для парсера
    os.makedirs(log_dir, exist_ok=True)

    # Основной лог файл для всех сообщений
    main_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "parser.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    main_handler.setLevel(log_level)
    main_handler.setFormatter(formatter)
    logger.addHandler(main_handler)

    # Отдельный файл только для ошибок и критических сообщений
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "parser_errors.log"),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # Отдельный файл для результатов парсинга
    results_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "parser_results.log"),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding="utf-8",
    )
    results_handler.setLevel(logging.INFO)
    results_handler.setFormatter(formatter)

    # Настраиваем отдельный логгер для результатов парсинга
    results_logger = logging.getLogger("parser_results")
    results_logger.addHandler(results_handler)
    results_logger.setLevel(logging.INFO)
    results_logger.propagate = False  # Не дублировать в основной лог

    # Уменьшаем шум от библиотек
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    setup_logging._configured = True  # type: ignore[attr-defined]


def get_results_logger() -> logging.Logger:
    """Получить логгер для результатов парсинга"""
    return logging.getLogger("parser_results")
