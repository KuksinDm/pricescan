import logging
import re
import time
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from constants import (
    DEFAULT_LIMIT,
    DEFAULT_USER_AGENT,
    EXCLUDED_CATEGORIES,
    HOBBYGAMES_SELECTORS,
)
from logging_config import get_results_logger
from settings import ParserSettings

from shared_models import ProductData


class BeautifulSoupParser:
    """Универсальный BeautifulSoup парсер для HTML сайтов с поддержкой HobbyGames"""

    def __init__(self, settings: ParserSettings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.results_logger = get_results_logger()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    @classmethod
    def create(cls, base_url: str = "https://hobbygames.ru") -> "BeautifulSoupParser":
        """Фабричный метод для создания парсера"""
        settings = ParserSettings(base_url=base_url)
        return cls(settings)

    def parse_product(self, url: str) -> Optional[ProductData]:
        """Парсинг одного товара"""
        try:
            time.sleep(self.settings.request_delay)
            response = self.session.get(url, timeout=self.settings.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")
            product = self._extract_product_data(soup, url)

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

    def parse_catalog(
        self,
        shop_url: str,
        limit: int = DEFAULT_LIMIT,
        page_start: int = 1,
        max_pages: int | None = None,
        detail: bool = False,
    ) -> List[ProductData]:
        """Парсинг каталога магазина с поддержкой пагинации.
        - page_start: с какой страницы начать (1-based)
        - max_pages: максимум страниц пройти за один вызов
        - detail: парсить детали товаров (медленнее, но полнее)
        """
        try:
            self.results_logger.info(
                f"BeautifulSoup parse_catalog called: shop_url={shop_url}, limit={limit}, "
                f"page_start={page_start}, max_pages={max_pages}, detail={detail}"
            )

            if not shop_url:
                self.logger.error("shop_url не может быть пустым")
                return []

            self.logger.info(f"Making request to: {shop_url}")
            time.sleep(self.settings.request_delay)

            # Добавить retry логику
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.session.get(
                        shop_url, timeout=60
                    )  # увеличить таймаут
                    response.raise_for_status()
                    break
                except requests.exceptions.Timeout as e:
                    if attempt == max_retries - 1:
                        self.logger.error(
                            f"Request failed after {max_retries} attempts: {e}"
                        )
                        return []
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(2**attempt)  # exponential backoff

            products: List[ProductData] = []

            # Генерируем URL'ы страниц программно (как в Playwright парсере)
            base_url = shop_url.split("?")[0]  # убираем существующие параметры
            page_urls = []

            for page_num in range(page_start, page_start + (max_pages or 12)):
                generated_url = f"{base_url}?page={page_num}&results_per_page=30"
                page_urls.append(generated_url)

            self.logger.info(f"Generated {len(page_urls)} page URLs: {page_urls[:5]}")

            seen_urls: set[str] = set()

            for page_url in page_urls:
                if len(products) >= limit:
                    break

                self.logger.info(f"Processing page: {page_url}")
                time.sleep(self.settings.request_delay)

                # Добавить retry для каждой страницы
                resp = None
                for attempt in range(max_retries):
                    try:
                        resp = self.session.get(page_url, timeout=60)
                        if resp.status_code == 200:
                            break
                    except requests.exceptions.Timeout:
                        if attempt == max_retries - 1:
                            self.logger.warning(
                                f"Skip page {page_url}: timeout after {max_retries} attempts"
                            )
                            resp = None
                            break
                        time.sleep(2**attempt)

                if resp is None or resp.status_code != 200:
                    self.logger.warning(
                        f"Skip page {page_url}: status={resp.status_code if resp else 'timeout'}"
                    )
                    continue

                page_soup = BeautifulSoup(resp.content, "lxml")
                chunk = self._extract_products_from_category(
                    page_soup, limit - len(products), page_url, detail=detail
                )

                # Дедуп по URL
                for p in chunk:
                    if p and p.url and p.url not in seen_urls:
                        products.append(p)
                        seen_urls.add(p.url)

                self.logger.info(
                    f"Page {page_url}: found {len(chunk)} products, total: {len(products)}"
                )

            self.results_logger.info(f"Extracted {len(products)} products from catalog")
            return products

        except Exception as e:
            self.logger.error(f"Error in parse_catalog: {e}")
            self.results_logger.error(f"BeautifulSoup parse_catalog failed: {e}")
            return []

    def _extract_product_data(
        self, soup: BeautifulSoup, url: str
    ) -> Optional[ProductData]:
        """Извлечение данных товара со страницы"""
        try:
            # Название
            title = self._extract_title(soup)
            if not title:
                return None

            # Цена
            price_rub = self._extract_price(soup)

            # Производители
            manufacturers = self._extract_manufacturers(soup)

            # Категории
            categories = self._extract_categories(soup)

            # Игровые характеристики
            players, play_time, age = self._extract_game_characteristics(soup)

            return ProductData(
                title=title,
                url=url,
                price_rub=price_rub,
                manufacturers=manufacturers,
                categories=categories,
                players=players,
                play_time=play_time,
                age=age,
            )

        except Exception as e:
            self.logger.error(f"Ошибка при извлечении данных товара: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение названия товара"""
        for selector in HOBBYGAMES_SELECTORS["title"]:
            element = soup.select_one(selector)
            if element:
                return element.get_text(" ", strip=True)
        return None

    def _extract_price(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлечение цены товара"""
        for selector in HOBBYGAMES_SELECTORS["price"]:
            element = soup.select_one(selector)
            if element:
                price = self._to_int(element.get_text(" ", strip=True))
                if price is not None:
                    return price
        return None

    def _extract_manufacturers(self, soup: BeautifulSoup) -> List[str]:
        """Извлечение производителей/издателей"""
        manufacturers = []

        # Логируем что ищем
        self.logger.debug("=== EXTRACTING MANUFACTURERS ===")

        # Проверяем, есть ли секция с производителями
        manufacturers_section = soup.select_one("#manufacturers")
        if manufacturers_section:
            self.logger.debug("Found #manufacturers section")
        else:
            self.logger.debug("No #manufacturers section found")

        # Ищем все элементы с производителями
        manufacturer_elements = soup.select(HOBBYGAMES_SELECTORS["manufacturers"][0])
        self.logger.debug(f"Found {len(manufacturer_elements)} manufacturer elements")

        # Если не нашли, пробуем другие селекторы
        if not manufacturer_elements:
            for selector in HOBBYGAMES_SELECTORS["manufacturers"][1:]:
                elements = soup.select(selector)
                self.logger.debug(
                    f"Selector '{selector}' found {len(elements)} elements"
                )
                if elements:
                    manufacturer_elements = elements
                    break

        for element in manufacturer_elements:
            manufacturer = element.get_text(" ", strip=True)
            self.logger.debug(f"Found manufacturer: '{manufacturer}'")
            if manufacturer and manufacturer not in manufacturers:
                manufacturers.append(manufacturer)

        self.logger.debug(f"Final manufacturers list: {manufacturers}")
        return manufacturers

    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        """Извлечение категорий"""
        categories = []

        for selector in HOBBYGAMES_SELECTORS["categories"]:
            elements = soup.select(selector)
            for element in elements:
                category = element.get_text(" ", strip=True)
                if (
                    category
                    and category not in categories
                    and category not in EXCLUDED_CATEGORIES
                ):
                    categories.append(category)

        return categories

    def _extract_game_characteristics(self, soup: BeautifulSoup) -> tuple:
        """Извлечение игровых характеристик"""
        self.logger.debug("Starting game characteristics extraction")

        # Сначала пробуем извлечь из таблиц атрибутов
        players = self._extract_players_from_attrs(soup)
        play_time = None
        age = None

        self.logger.debug(f"Players from attributes: {players}")

        # Потом ищем в тегах
        for selector in HOBBYGAMES_SELECTORS["game_tags"]:
            tags = soup.select(selector)
            self.logger.debug(f"Selector '{selector}' found {len(tags)} tags")

            for tag in tags:
                tag_text = tag.get_text(" ", strip=True)
                self.logger.debug(f"Processing tag: '{tag_text}'")

                # Количество игроков (формат "1-2", "3-4" и т.д.)
                if (
                    "-" in tag_text
                    and tag_text.replace("-", "").replace(" ", "").isdigit()
                ):
                    if not players:
                        players = self._parse_range(tag_text)
                        self.logger.debug(f"Found players from tags: {players}")

                # Время партии (формат "60-120", "30-45" и т.д.)
                if "-" in tag_text and any(char.isdigit() for char in tag_text):
                    nums = [int(x) for x in tag_text.split("-") if x.strip().isdigit()]
                    if nums:  # убрали ограничение >= 30
                        if not play_time:
                            play_time = self._parse_range(tag_text)
                            self.logger.debug(f"Found play_time from tags: {play_time}")

                # Возраст (формат "14+", "8+", "18+" и т.д.)
                if "+" in tag_text:
                    if not age:
                        age = self._parse_range(tag_text)
                        self.logger.debug(f"Found age from tags: {age}")

        self.logger.debug(
            f"Final characteristics: players={players}, play_time={play_time}, age={age}"
        )
        return players, play_time, age

    def _extract_players_from_attrs(self, soup: BeautifulSoup) -> Optional[str]:
        """Ищем 'Количество игроков' в таблицах атрибутов"""
        for tr in soup.select(
            "#attributes table tr, section#attributes table tr, table tr"
        ):
            tds = tr.find_all(["td", "th"])
            if len(tds) < 2:
                continue
            key = tds[0].get_text(" ", strip=True).lower()
            if re.search(r"игрок", key):
                val = tds[1].get_text(" ", strip=True)
                val = val.replace("–", "-").replace("—", "-")
                rng = self._parse_range(val)
                if rng:
                    self.logger.debug(f"Players from attributes: {rng}")
                    return rng
        return None

    def _extract_products_from_category(
        self,
        soup: BeautifulSoup,
        limit: int,
        shop_url: str = None,
        detail: bool = False,
    ) -> List[ProductData]:
        """Извлечение товаров из категории"""
        products: List[ProductData] = []

        if not shop_url:
            self.logger.error("shop_url не может быть пустым")
            return products

        # Ищем ссылки на товары
        links = self._find_product_links(soup)

        if not links:
            self.logger.error("No product links found on page")
            return products

        # Парсим найденные ссылки
        for a in links[:limit]:
            title = (a.get_text(strip=True) if a else None) or ""
            url = (a.get("href") if a else None) or ""

            if not url or not title:
                continue

            # Абсолютизируем URL
            if url.startswith("/"):
                url = urljoin(shop_url, url)

            # Получаем базовую информацию с карточки (с листинга)
            card = a.find_parent(class_=lambda c: c and "product-card" in c) or a.parent
            price_rub = None
            if card:
                price_el = card.select_one(
                    '.product-card-price, .product-price, .price, [data-entity="price-current"] .price-value'
                )
                if price_el:
                    price_rub = self._to_int(price_el.get_text(" ", strip=True))

            # Базовый ProductData
            base_product = ProductData(
                title=title,
                url=url,
                price_rub=price_rub,
                manufacturers=[],
                categories=[],
                players=None,
                play_time=None,
                age=None,
            )

            # detail=True → дополняем из карточки товара
            try:
                time.sleep(self.settings.request_delay)
                product_response = self.session.get(url, timeout=self.settings.timeout)
                product_response.raise_for_status()
                product_soup = BeautifulSoup(product_response.content, "lxml")

                full_product = self._extract_product_data(product_soup, url)
                if full_product:
                    merged_product = ProductData(
                        title=full_product.title or base_product.title,
                        url=url,
                        price_rub=full_product.price_rub or base_product.price_rub,
                        manufacturers=full_product.manufacturers
                        or base_product.manufacturers,
                        categories=full_product.categories or base_product.categories,
                        players=full_product.players,
                        play_time=full_product.play_time,
                        age=full_product.age,
                    )
                    products.append(merged_product)
                    self.logger.info(
                        f"Successfully parsed product: {merged_product.title}"
                    )
                else:
                    products.append(base_product)
                    self.logger.warning(f"Used basic parsing for: {title}")

            except Exception as e:
                self.logger.warning(f"Failed to parse product page {url}: {e}")
                products.append(base_product)
                self.logger.warning(f"Used basic parsing for: {title}")

        self.logger.info(f"Extracted {len(products)} products from catalog")
        return products

    def _find_product_links(self, soup: BeautifulSoup) -> List:
        """Поиск ссылок на товары"""
        links = []

        # Современная разметка HobbyGames
        for selector in HOBBYGAMES_SELECTORS["product_links"]:
            found_links = soup.select(selector)
            if found_links:
                self.logger.info(
                    f"Found {len(found_links)} links with selector: {selector}"
                )
                links = found_links
                break

        # Если ничего не нашли, пробуем карточки
        if not links:
            product_cards = soup.select(
                ", ".join(HOBBYGAMES_SELECTORS["product_cards"])
            )
            for card in product_cards:
                link = card.select_one("a[href]")
                if link:
                    links.append(link)
            self.logger.info(f"Found {len(links)} links from product cards")

        return links

    def _to_int(self, text: str) -> Optional[int]:
        """Конвертация текста в число"""
        if text is None:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else None

    def _parse_range(self, text: str) -> Optional[str]:
        if not text:
            return None
        s = text.strip().replace("–", "-").replace("—", "-")
        cleaned = re.sub(r"[^\d\-\+]", "", s)
        return cleaned if cleaned else None

    def _find_pagination_urls(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Ищет ссылки пагинации и возвращает абсолютные URL в порядке появления"""
        selectors = [
            "ul.pagination a[href]",
            ".pagination a[href]",
            "nav.pagination a[href]",
            ".paginate a[href]",
            "a[rel='next']",
            "li.next a[href]",
            "a.next[href]",
            "a[href*='page=']",
        ]
        seen: set[str] = set()
        urls: list[str] = []
        for sel in selectors:
            for a in soup.select(sel):
                href = a.get("href")
                if not href:
                    continue
                full = urljoin(current_url, href)
                if full not in seen:
                    seen.add(full)
                    urls.append(full)
        return urls
