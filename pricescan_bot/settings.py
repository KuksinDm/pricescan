import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Настройки приложения бота"""

    bot_token: str
    api_base_url: str
    service_token: str
    log_level: str = "INFO"
    api_timeout: int = 15

    @staticmethod
    def from_env() -> "Settings":
        """Загружает настройки из переменных окружения"""
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        api_base_url = os.getenv(
            "API_BASE_URL", "http://web-pricescan:9040/api/"
        ).strip()
        service_token = os.getenv("BOT_SERVICE_TOKEN", "").strip()
        log_level = os.getenv("BOT_LOG_LEVEL", "INFO").strip().upper()
        api_timeout = int(os.getenv("API_TIMEOUT", "15"))

        if not bot_token:
            raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

        if not service_token:
            raise RuntimeError("BOT_SERVICE_TOKEN не задан в переменных окружения")

        if not api_base_url.startswith(("http://", "https://")):
            raise RuntimeError(f"Некорректный API_BASE_URL: {api_base_url}")

        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if log_level not in valid_levels:
            raise RuntimeError(
                f"Некорректный BOT_LOG_LEVEL: {log_level}. Доступные: {valid_levels}"
            )

        return Settings(
            bot_token=bot_token,
            api_base_url=api_base_url,
            service_token=service_token,
            log_level=log_level,
            api_timeout=api_timeout,
        )

    def __post_init__(self):
        if not self.api_base_url.endswith("/"):
            self.api_base_url += "/"

        if self.api_timeout <= 0:
            raise ValueError("API_TIMEOUT должен быть положительным числом")
