import asyncio
import logging
from typing import Optional

from constants import DEFAULT_CONCURRENCY, DEFAULT_USER_AGENT
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from settings import PlaywrightSettings


class PlaywrightBrowser:
    """Клиент для работы с Playwright браузером"""

    def __init__(self, settings: PlaywrightSettings):
        self.settings = settings
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._semaphore = asyncio.Semaphore(DEFAULT_CONCURRENCY)
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Инициализация браузера"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.settings.headless
        )
        self._context = await self._browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport=self.settings.viewport_size,
            locale="ru-RU",
        )
        await self._setup_request_blocking()

    async def close(self):
        """Закрытие браузера"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def new_page(self) -> Page:
        """Создание новой страницы"""
        if not self._context:
            raise RuntimeError("Browser not initialized")
        return await self._context.new_page()

    async def with_semaphore(self, coro):
        """Выполнение с семафором"""
        async with self._semaphore:
            return await coro

    async def _setup_request_blocking(self):
        """Настройка блокировки ненужных запросов"""
        if not self._context:
            return

        async def handler(route, request):
            t = request.resource_type
            u = request.url
            if t in {"image", "media", "font"} or any(
                s in u
                for s in (
                    "google-analytics",
                    "gtag/js",
                    "metrika",
                    "mc.yandex",
                    "doubleclick",
                    "facebook",
                    "vk.com/rtrg",
                    "pixel",
                    "metrics",
                )
            ):
                await route.abort()
            else:
                await route.continue_()

        await self._context.route("**/*", handler)
