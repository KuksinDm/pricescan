# pricescan_playwright/parser/playwright_parser.py
import asyncio
import logging
from typing import List, Optional

from constants import (
    AGE_GATE_SELECTORS,
    BLACKLIST_SUBSTR,
    CONTAINER_SELECTOR,
    CONTENT_SELECTOR,
    COOKIE_SELECTORS,
    DEFAULT_AGE_GATE_TIMEOUT,
    DEFAULT_AUTO_SCROLL_TIMEOUT,
    DEFAULT_COOKIE_TIMEOUT,
    DEFAULT_LIMIT,
    DEFAULT_MAX_PAGES,
    DEFAULT_PAGE_START,
    DEFAULT_PAGE_WAIT,
    DEFAULT_RESULTS_PER_PAGE,
    DEFAULT_SCROLL_DELAY,
    DEFAULT_SELECTOR_TIMEOUT,
    DEFAULT_TIMEOUT_MS,
    DEFAULT_UI_DELAY,
    PRODUCT_CARD_SELECTOR,
    PRODUCT_LINK_SELECTORS,
)
from playwright.async_api import Page
from utils.browser_client import PlaywrightBrowser
from utils.data_extractor import PlaywrightDataExtractor

from shared_models import ProductData


class PlaywrightParser:
    """Упрощенный Playwright парсер с DI"""

    def __init__(
        self, browser_client: PlaywrightBrowser, data_extractor: PlaywrightDataExtractor
    ):
        self.browser_client = browser_client
        self.data_extractor = data_extractor
        self.logger = logging.getLogger(__name__)

    async def parse_product(self, url: str) -> Optional[ProductData]:
        """Парсинг одного товара"""
        page = await self.browser_client.new_page()
        try:
            await page.goto(
                url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS
            )
            await self._handle_ui_elements(page)

            # Ждем загрузки контента
            try:
                await page.wait_for_selector(
                    CONTENT_SELECTOR, timeout=DEFAULT_SELECTOR_TIMEOUT
                )
            except Exception:
                pass

            title = await self.data_extractor.extract_title(page)
            if not title:
                self.logger.warning(f"parse_product: no title for {url}")
                return None

            price = await self.data_extractor.extract_price(page)
            attrs = await self.data_extractor.extract_attributes(page)
            categories = await self.data_extractor.extract_categories(page)

            # ВСЕ извлечение данных делегируем в data_extractor
            manufacturers = self.data_extractor.extract_manufacturers(attrs)
            players = self.data_extractor.extract_players(attrs)
            play_time = self.data_extractor.extract_play_time(attrs)
            age = self.data_extractor.extract_age(attrs)

            return ProductData(
                title=title,
                url=url,
                price_rub=price,
                manufacturers=manufacturers,
                categories=categories,
                players=players,
                play_time=play_time,
                age=age,
            )
        finally:
            await page.close()

    async def parse_catalog(
        self,
        shop_url: str,
        limit: int = DEFAULT_LIMIT,
        page_start: int = DEFAULT_PAGE_START,
        max_pages: int | None = None,
    ) -> List[ProductData]:
        page = await self.browser_client.new_page()
        try:
            await page.goto(
                shop_url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS
            )
            await self._handle_ui_elements(page)

            links = await self._collect_links(page, limit, page_start, max_pages)
            self.logger.info(f"parse_catalog: links={len(links)}")

            if not links:
                return []

            async def worker(url: str):
                return await self.browser_client.with_semaphore(self.parse_product(url))

            results = await asyncio.gather(*(worker(url) for url in links))
            successful_results = [result for result in results if result]
            self.logger.info(f"parse_catalog: parsed={len(successful_results)}")
            return successful_results
        finally:
            await page.close()

    async def _handle_ui_elements(self, page: Page):
        await self._maybe_close_cookies(page)
        await self._maybe_handle_age_gate(page)

    async def _maybe_close_cookies(self, page: Page):
        for selector in COOKIE_SELECTORS:
            try:
                loc = page.locator(selector).first
                if await loc.is_visible(timeout=DEFAULT_COOKIE_TIMEOUT):
                    await loc.click(timeout=DEFAULT_COOKIE_TIMEOUT)
                    await page.wait_for_timeout(DEFAULT_UI_DELAY)
                    break
            except Exception:
                pass

    async def _maybe_handle_age_gate(self, page: Page):
        try:
            visible = await page.locator("text=Подтвердите возраст").first.is_visible(
                timeout=DEFAULT_AGE_GATE_TIMEOUT
            )
        except Exception:
            visible = False

        if visible:
            for selector in AGE_GATE_SELECTORS:
                try:
                    loc = page.locator(selector).first
                    if await loc.is_visible(timeout=DEFAULT_AGE_GATE_TIMEOUT):
                        await loc.click(timeout=DEFAULT_AGE_GATE_TIMEOUT)
                        await page.wait_for_timeout(DEFAULT_UI_DELAY)
                        break
                except Exception:
                    continue

    async def _collect_links(
        self, page: Page, limit: int, page_start: int, max_pages: int | None
    ) -> List[str]:
        links: List[str] = []
        seen: set[str] = set()

        async def collect_here():
            nonlocal links
            batch = await self._get_catalog_links(page, limit - len(links))
            for url in batch:
                if url not in seen:
                    seen.add(url)
                    links.append(url)

        await collect_here()
        if len(links) >= limit:
            return links[:limit]

        base_url = page.url.split("?")[0]
        page_urls = []

        for page_num in range(
            page_start, page_start + (max_pages or DEFAULT_MAX_PAGES)
        ):
            generated_url = f"{base_url}?page={page_num}&results_per_page={DEFAULT_RESULTS_PER_PAGE}"
            page_urls.append(generated_url)

        self.logger.info(f"Generated {len(page_urls)} page URLs: {page_urls[:5]}")

        for page_url in page_urls:
            if len(links) >= limit:
                break
            try:
                await page.goto(
                    page_url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS
                )
                await self._handle_ui_elements(page)
                await collect_here()
            except Exception:
                continue

        return links[:limit]

    async def _get_catalog_links(self, page: Page, limit: int) -> List[str]:
        container_selector = CONTAINER_SELECTOR
        try:
            await page.wait_for_selector(
                container_selector, timeout=DEFAULT_SELECTOR_TIMEOUT
            )
        except Exception:
            pass

        await self._auto_scroll(page, limit, DEFAULT_AUTO_SCROLL_TIMEOUT)

        origin = "/".join(page.url.split("/", 3)[:3])
        seen: set[str] = set()
        out: List[str] = []

        for selector in PRODUCT_LINK_SELECTORS:
            try:
                batch: List[str] = await page.eval_on_selector_all(
                    selector,
                    "elements => Array.from(new Set(elements.map(element => element.getAttribute('href') || element.href).filter(Boolean)))",
                )
                self.logger.info(
                    f"_get_catalog_links: selector '{selector}' found {len(batch)} links"
                )
            except Exception as e:
                self.logger.warning(
                    f"_get_catalog_links: selector '{selector}' failed: {e}"
                )
                batch = []

            for href in batch:
                full_url = self._absolutize(origin, href)
                if any(blocked in full_url for blocked in BLACKLIST_SUBSTR):
                    continue
                if full_url in seen:
                    continue
                seen.add(full_url)
                out.append(full_url)
                if len(out) >= limit:
                    return out[:limit]

        return out[:limit]

    async def _auto_scroll(
        self,
        page: Page,
        target_count: int,
        time_budget_ms: int = DEFAULT_AUTO_SCROLL_TIMEOUT,
    ):
        """Автопрокрутка для загрузки контента"""
        import time

        deadline = time.time() + time_budget_ms / 1000
        previous_count = -1
        while time.time() < deadline:
            try:
                current_count = await page.locator(PRODUCT_CARD_SELECTOR).count()
            except Exception:
                current_count = 0
            if current_count >= target_count:
                break
            if current_count == previous_count:
                await page.wait_for_timeout(DEFAULT_PAGE_WAIT)
                break
            previous_count = current_count
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_timeout(DEFAULT_SCROLL_DELAY)

    def _absolutize(self, origin: str, href: str) -> str:
        """Преобразование относительного URL в абсолютный"""
        return origin + href if href.startswith("/") else href
