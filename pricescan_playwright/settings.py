import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class PlaywrightSettings:
    base_url: str
    timeout: int = 12
    headless: bool = True
    viewport_width: int = 1366
    viewport_height: int = 900
    log_level: str = "INFO"
    log_dir: Optional[str] = None

    @staticmethod
    def from_env() -> "PlaywrightSettings":
        base_url = os.getenv("PARSER_BASE_URL", "https://www.mosigra.ru").strip()
        timeout = int(os.getenv("PARSER_TIMEOUT", "12"))
        headless = os.getenv("PARSER_HEADLESS", "true").lower() == "true"
        log_level = os.getenv("PARSER_LOG_LEVEL", "INFO").strip().upper()
        log_dir = os.getenv("PARSER_LOG_DIR")
        return PlaywrightSettings(
            base_url=base_url,
            timeout=timeout,
            headless=headless,
            log_level=log_level,
            log_dir=log_dir,
        )

    @property
    def viewport_size(self) -> dict:
        return {"width": self.viewport_width, "height": self.viewport_height}
