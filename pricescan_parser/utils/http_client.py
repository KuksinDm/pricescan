import asyncio
import logging
from typing import Optional

import aiohttp
from constants import (
    DEFAULT_CONNECTOR_LIMIT,
    DEFAULT_CONNECTOR_LIMIT_PER_HOST,
    DEFAULT_CONNECTOR_TTL_DNS_CACHE,
    DEFAULT_CONNECTOR_USE_DNS_CACHE,
    DEFAULT_MAX_CONCURRENT_REQUESTS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
)


class AsyncHttpClient:
    """Асинхронный HTTP клиент с семафором для контроля нагрузки"""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        request_delay: float = DEFAULT_REQUEST_DELAY,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT_REQUESTS,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.max_concurrent = max_concurrent
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = logging.getLogger(__name__)

    @property
    def session(self) -> aiohttp.ClientSession:
        """Получает или создает HTTP сессию"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                },
                connector=aiohttp.TCPConnector(
                    limit=DEFAULT_CONNECTOR_LIMIT,
                    limit_per_host=DEFAULT_CONNECTOR_LIMIT_PER_HOST,
                    ttl_dns_cache=DEFAULT_CONNECTOR_TTL_DNS_CACHE,
                    use_dns_cache=DEFAULT_CONNECTOR_USE_DNS_CACHE,
                ),
            )
        return self._session

    async def get(self, url: str, **kwargs) -> bytes:
        """Выполняет GET запрос с retry логикой"""
        async with self._semaphore:
            max_retries = DEFAULT_MAX_RETRIES

            for attempt in range(max_retries):
                try:
                    await asyncio.sleep(self.request_delay)
                    async with self.session.get(url, **kwargs) as response:
                        response.raise_for_status()
                        return await response.read()
                except aiohttp.ClientTimeout as e:
                    if attempt == max_retries - 1:
                        self.logger.error(
                            f"Request failed after {max_retries} attempts: {e}"
                        )
                        raise
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                    await asyncio.sleep(2**attempt)
                except aiohttp.ClientError as e:
                    self.logger.error(f"HTTP error for {url}: {e}")
                    raise
                except Exception as e:
                    self.logger.error(f"Unexpected error for {url}: {e}")
                    raise

    async def close(self):
        """Закрывает соединения"""
        if self._session and not self._session.closed:
            await self._session.close()
