from typing import Optional

from settings import ParserSettings
from utils.extractors import DataExtractor
from utils.http_client import AsyncHttpClient


class ParserContainer:
    """Dependency Injection контейнер для парсера - как в боте"""

    def __init__(self):
        self._settings: Optional[ParserSettings] = None
        self._http_client: Optional[AsyncHttpClient] = None
        self._data_extractor: Optional[DataExtractor] = None

    async def initialize(self):
        """Инициализация всех компонентов"""
        self._settings = ParserSettings.from_env()
        self._http_client = AsyncHttpClient(
            timeout=self._settings.timeout, request_delay=self._settings.request_delay
        )
        self._data_extractor = DataExtractor()

    async def cleanup(self):
        """Очистка ресурсов"""
        if self._http_client:
            await self._http_client.close()

    @property
    def settings(self) -> ParserSettings:
        if not self._settings:
            raise RuntimeError("Container not initialized")
        return self._settings

    @property
    def http_client(self) -> AsyncHttpClient:
        if not self._http_client:
            raise RuntimeError("Container not initialized")
        return self._http_client

    @property
    def data_extractor(self) -> DataExtractor:
        if not self._data_extractor:
            raise RuntimeError("Container not initialized")
        return self._data_extractor


# Глобальный контейнер
container = ParserContainer()
