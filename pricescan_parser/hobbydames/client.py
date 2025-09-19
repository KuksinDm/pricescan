import asyncio
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HobbyGamesClient:
    """HTTP клиент для работы с HobbyGames.ru"""

    BASE_URL = "https://hobbygames.ru/"
    SEARCH_URL = "https://hobbygames.ru/search/"

    def __init__(self, timeout: int = 30, rate_limit: int = 1):
        self.timeout = timeout
        self.rate_limit = rate_limit  # секунд между запросами
        self._last_request_time = None
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def _wait_rate_limit(self):
        """Соблюдение ограничения скорости запросов"""
        if self._last_request_time:
            elapsed = datetime.now() - self._last_request_time
            if elapsed.total_seconds() < self.rate_limit:
                await asyncio.sleep(self.rate_limit - elapsed.total_seconds())

        self._last_request_time = datetime.now()

    async def get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Получить HTML страницу с повторными попытками"""
        await self._wait_rate_limit()
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, headers=self.headers, follow_redirects=True
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    encoding = response.encoding or "utf-8"
                    html_content = response.content.decode(encoding, errors="ignore")

                    return BeautifulSoup(html_content, "lxml")

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt < retries - 1:
                    wait_time = 2**attempt  # Экспоненциальная задержка
                    logger.warning(
                        f"Попытка {attempt + 1} неудачна для {url}: {e}. "
                        f"Повтор через {wait_time}с"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Все попытки исчерпаны для {url}: {e}")
                    return None
            except Exception as e:
                logger.error(f"Неожиданная ошибка при получении {url}: {e}")
                return None

        return None

    async def get_product_page(self, url: str) -> Optional[BeautifulSoup]:
        """Получить страницу конкретного товара"""
        if not url.startswith("http"):
            url = urljoin(self.BASE_URL, url)

        return await self.get_page(url)

    async def get_category_page(
        self, category_url: str, page: int = 1
    ) -> Optional[BeautifulSoup]:
        """Получить страницу категории товаров"""
        if not category_url.startswith("http"):
            category_url = urljoin(self.BASE_URL, category_url)

        if page > 1:
            category_url = f"{category_url}?page={page}"

        return await self.get_page(category_url)

    async def close(self):
        """Закрыть соединения (для совместимости)"""
        pass
