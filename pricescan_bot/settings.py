import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str
    api_base_url: str
    service_token: str

    @staticmethod
    def from_env() -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        api = os.getenv("API_BASE_URL", "http://web-pricescan:9040/api/").strip()
        service = os.getenv("BOT_SERVICE_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN не задан")
        return Settings(bot_token=token, api_base_url=api, service_token=service)
