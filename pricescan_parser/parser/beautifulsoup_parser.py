# pricescan_parser/parser/beautifulsoup_parser.py
import asyncio
import logging
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from constants import DEFAULT_BATCH_SIZE, DEFAULT_LIMIT, DEFAULT_PAGE_START
from logging_config import get_results_logger
from utils.extractors import DataExtractor
from utils.http_client import AsyncHttpClient

from shared_models import ProductData


class BeautifulSoupParser:
    def __init__(self, http_client: AsyncHttpClient, data_extractor: DataExtractor):
        self.http_client = http_client
        self.data_extractor = data_extractor
        self.logger = logging.getLogger(__name__)
        self.results_logger = get_results_logger()

    async def parse_product(self, url: str) -> Optional[ProductData]:
        try:
            self.results_logger.info(f"parse_product: {url}")
            content = await self.http_client.get(url)
            soup = BeautifulSoup(content, "lxml")

            title = self.data_extractor.extract_title(soup)
            if not title:
                return None

            price_rub = self.data_extractor.extract_price(soup)
            manufacturers = self.data_extractor.extract_manufacturers(soup)
            categories = self.data_extractor.extract_categories(soup)
            players, play_time, age = self.data_extractor.extract_game_characteristics(
                soup
            )

            product = ProductData(
                title=title,
                url=url,
                price_rub=price_rub,
                manufacturers=manufacturers,
                categories=categories,
                players=players,
                play_time=play_time,
                age=age,
            )

            if product:
                self.results_logger.info(
                    f"Successfully parsed product: {product.title}"
                )
            else:
                self.logger.warning(f"Failed to parse product from: {url}")

            return product

        except Exception as e:
            self.logger.error(f"Ошибка при парсинге {url}: {e}")
            return None

    async def parse_catalog(
        self,
        shop_url: str,
        limit: int = DEFAULT_LIMIT,
        page_start: int = DEFAULT_PAGE_START,
        max_pages: int | None = None,
        detail: bool = False,
    ) -> List[ProductData]:
        """Парсинг каталога магазина с батчами"""
        try:
            self.results_logger.info(
                f"parse_catalog: url={shop_url}, limit={limit}, "
                f"page_start={page_start}, max_pages={max_pages}, detail={detail}"
            )

            if not shop_url:
                self.logger.error("shop_url не может быть пустым")
                return []

            page_urls = self._generate_page_urls(shop_url, page_start, max_pages)
            base_url = shop_url.split("?")[0]
            return await self._process_pages_in_batches(
                page_urls, limit, detail, base_url
            )

        except Exception as e:
            self.logger.error(f"Error in parse_catalog: {e}")
            self.results_logger.error(f"BeautifulSoup parse_catalog failed: {e}")
            return []

    def _generate_page_urls(
        self, shop_url: str, page_start: int, max_pages: int
    ) -> List[str]:
        """Генерирует URL страниц для разных магазинов"""
        base_url = shop_url.split("?")[0]
        page_urls = []

        for page_num in range(page_start, page_start + (max_pages or 12)):
            generated_url = f"{base_url}?page={page_num}"
            page_urls.append(generated_url)

        self.results_logger.info(
            f"Generated {len(page_urls)} page URLs: {page_urls[:5]}..."
        )
        return page_urls

    async def _process_pages_in_batches(
        self, page_urls: List[str], limit: int, detail: bool, base_url: str
    ) -> List[ProductData]:
        products: List[ProductData] = []
        seen_urls: set[str] = set()
        batch_size = DEFAULT_BATCH_SIZE

        for i in range(0, len(page_urls), batch_size):
            if len(products) >= limit:
                self.logger.info(f"Reached total limit {limit}, stopping")
                break

            batch_urls = page_urls[i : i + batch_size]
            self.logger.info(
                f"Processing batch {i // batch_size + 1}: {len(batch_urls)} pages"
            )

            batch_products = await self._process_single_batch(
                batch_urls, limit - len(products), detail, base_url
            )

            for product in batch_products:
                if product and product.url and product.url not in seen_urls:
                    products.append(product)
                    seen_urls.add(product.url)
                    if len(products) >= limit:
                        break

        self.results_logger.info(f"Extracted {len(products)} products from catalog")
        return products

    async def _process_single_batch(
        self, batch_urls: List[str], limit: int, detail: bool, base_url: str
    ) -> List[ProductData]:
        tasks = []
        for page_url in batch_urls:
            task = self._process_page_async(page_url, limit, base_url, detail)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        batch_products = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.warning(f"Page processing failed: {result}")
                continue
            batch_products.extend(result)

        return batch_products

    async def _process_page_async(
        self, page_url: str, limit: int, base_url: str, detail: bool
    ) -> List[ProductData]:
        try:
            self.results_logger.info(f"Processing page: {page_url}")
            content = await self.http_client.get(page_url)
            soup = BeautifulSoup(content, "lxml")

            if detail:
                page_products = await self._parse_catalog_page_detailed(
                    soup, limit, base_url
                )
            else:
                page_products = await self._parse_catalog_page_fast(
                    soup, limit, base_url
                )

            self.results_logger.info(
                f"Page {page_url}: found {len(page_products)} products"
            )
            return page_products

        except Exception as e:
            self.logger.warning(f"Failed to parse page {page_url}: {e}")
            return []

    async def _parse_catalog_page_fast(
        self, soup: BeautifulSoup, limit: int, base_url: str
    ) -> List[ProductData]:
        products = []
        links = self.data_extractor.find_product_links(soup)

        self.results_logger.info(f"Found {len(links)} product links on page")

        for link in links:
            if len(products) >= limit:
                self.logger.info(f"Reached page limit {limit}, stopping")
                break

            try:
                title = link.get_text(strip=True) or ""
                url = link.get("href") or ""

                if not url or not title:
                    continue

                if url.startswith("/"):
                    url = urljoin(base_url, url)

                card = (
                    link.find_parent(class_=lambda c: c and "product-card" in c)
                    or link.parent
                )
                price_rub = None
                if card:
                    price_rub = DataExtractor.extract_price_from_element(card)

                product = ProductData(
                    title=title,
                    url=url,
                    price_rub=price_rub,
                    manufacturers=[],
                    categories=[],
                    players=None,
                    play_time=None,
                    age=None,
                )
                products.append(product)

            except Exception as e:
                self.logger.warning(f"Failed to extract product from link: {e}")
                continue

        self.results_logger.info(
            f"Fast parsing completed: {len(products)} products extracted"
        )
        return products

    async def _parse_catalog_page_detailed(
        self, soup: BeautifulSoup, limit: int, base_url: str
    ) -> List[ProductData]:
        products = []
        links = self.data_extractor.find_product_links(soup)

        self.results_logger.info(
            f"Detailed parsing: found {len(links)} product links on page"
        )

        for link in links:
            if len(products) >= limit:
                self.logger.info(f"Reached page limit {limit}, stopping")
                break

            try:
                title = link.get_text(strip=True) or ""
                url = link.get("href") or ""

                if not url or not title:
                    continue

                if url.startswith("/"):
                    url = urljoin(base_url, url)

                self.results_logger.info(f"parse_product: {url}")
                product = await self.parse_product(url)
                if product:
                    products.append(product)
                    self.logger.debug(
                        f"Successfully parsed detailed product: {product.title}"
                    )
                else:
                    self.logger.warning(
                        f"Failed to parse detailed product, skipping: {url}"
                    )

            except Exception as e:
                self.logger.warning(f"Failed to parse product from link: {e}")
                continue

        self.results_logger.info(
            f"Detailed parsing completed: {len(products)} products extracted"
        )
        return products
