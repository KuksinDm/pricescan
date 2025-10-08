# pricescan_playwright/container.py
from typing import Optional

from settings import PlaywrightSettings
from utils.browser_client import PlaywrightBrowser
from utils.data_extractor import PlaywrightDataExtractor


class PlaywrightContainer:
    """Dependency Injection контейнер для Playwright парсера"""

    def __init__(self):
        self._settings: Optional[PlaywrightSettings] = None
        self._browser_client: Optional[PlaywrightBrowser] = None
        self._data_extractor: Optional[PlaywrightDataExtractor] = None

    async def initialize(self):
        """Инициализация всех компонентов"""
        self._settings = PlaywrightSettings.from_env()
        self._browser_client = PlaywrightBrowser(self._settings)
        self._data_extractor = PlaywrightDataExtractor()

    async def cleanup(self):
        """Очистка ресурсов"""
        if self._browser_client:
            await self._browser_client.close()

    @property
    def settings(self) -> PlaywrightSettings:
        if not self._settings:
            raise RuntimeError("Container not initialized")
        return self._settings

    @property
    def browser_client(self) -> PlaywrightBrowser:
        if not self._browser_client:
            raise RuntimeError("Container not initialized")
        return self._browser_client

    @property
    def data_extractor(self) -> PlaywrightDataExtractor:
        if not self._data_extractor:
            raise RuntimeError("Container not initialized")
        return self._data_extractor


# Глобальный контейнер
container = PlaywrightContainer()
