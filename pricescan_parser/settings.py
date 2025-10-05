import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ParserSettings:
    """Настройки BeautifulSoup парсера"""

    base_url: str
    max_retries: int = 3
    timeout: int = 60
    request_delay: float = 0.5
    log_level: str = "INFO"
    log_dir: Optional[str] = None

    @staticmethod
    def from_env() -> "ParserSettings":
        """Загружает настройки из переменных окружения"""
        base_url = os.getenv("PARSER_BASE_URL", "https://hobbygames.ru").strip()
        max_retries = int(os.getenv("PARSER_MAX_RETRIES", "3"))
        timeout = int(os.getenv("PARSER_TIMEOUT", "30"))
        request_delay = float(os.getenv("PARSER_REQUEST_DELAY", "0.5"))
        log_level = os.getenv("PARSER_LOG_LEVEL", "INFO").strip().upper()
        log_dir = os.getenv("PARSER_LOG_DIR")

        # Валидация URL
        if not base_url.startswith(("http://", "https://")):
            raise RuntimeError(f"Некорректный PARSER_BASE_URL: {base_url}")

        # Валидация уровня логирования
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if log_level not in valid_levels:
            raise RuntimeError(
                f"Некорректный PARSER_LOG_LEVEL: {log_level}. Доступные: {valid_levels}"
            )

        return ParserSettings(
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            request_delay=request_delay,
            log_level=log_level,
            log_dir=log_dir,
        )

    def __post_init__(self):
        """Дополнительная валидация после создания объекта"""
        # Убеждаемся, что URL заканчивается на /
        if not self.base_url.endswith("/"):
            self.base_url += "/"

        # Валидация числовых параметров
        if self.max_retries <= 0:
            raise ValueError("max_retries должен быть положительным числом")

        if self.timeout <= 0:
            raise ValueError("timeout должен быть положительным числом")

        if self.request_delay < 0:
            raise ValueError("request_delay не может быть отрицательным")
