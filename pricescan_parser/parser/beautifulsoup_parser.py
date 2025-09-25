import logging
import re
import time
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from shared_models import ProductData


class BeautifulSoupParser:
    """Универсальный BeautifulSoup парсер для HTML сайтов с поддержкой HobbyGames"""

    def __init__(self, base_url: str, max_retries: int = 3):
        self.base_url = base_url
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def parse_product(self, url: str) -> Optional[ProductData]:
        """Парсинг одного товара"""
        try:
            time.sleep(0.5)  # Задержка как в примере
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")
            return self._extract_product_data(soup, url)

        except Exception as e:
            self.logger.error(f"Ошибка при парсинге {url}: {e}")
            return None

    def parse_catalog(self, shop_url: str, limit: int = 500) -> List[ProductData]:
        """Парсинг каталога магазина"""
        try:
            if not shop_url:
                self.logger.error("shop_url не может быть пустым")
                return []

            time.sleep(0.5)  # Задержка
            response = self.session.get(shop_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")
            return self._extract_products_from_category(soup, limit, shop_url)
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге каталога: {e}")
            return []

    def _extract_product_data(
        self, soup: BeautifulSoup, url: str
    ) -> Optional[ProductData]:
        """Извлечение данных товара со страницы (логика из примера HobbyGames)"""
        try:
            # Название - используем селекторы из примера
            title = None
            h1 = soup.select_one(".product-info__main h1, h1")
            if h1:
                title = h1.get_text(" ", strip=True)

            if not title:
                return None

            # Цена - используем селекторы из примера
            price_rub = None
            price_sel_candidates = [
                ".product-card-price__current",
                ".product-card-price_current",
                ".product-price__current",
                ".product-price, .price",
            ]
            for sel in price_sel_candidates:
                el = soup.select_one(sel)
                if el:
                    price_rub = self._to_int(el.get_text(" ", strip=True))
                    if price_rub is not None:
                        break

            # Описание - логика из примера
            description = None
            desc = soup.select_one("#desc.desc-text")
            if desc:
                parts = [p.get_text(" ", strip=True) for p in desc.select("p")]
                description = "\n\n".join([p for p in parts if p])
            else:
                desc = soup.select_one(".desc-text, .product-description")
                if desc:
                    parts = [p.get_text(" ", strip=True) for p in desc.select("p")]
                    description = "\n\n".join([p for p in parts if p])

            # Производитель - используем селекторы из примера
            manufacturer = None
            manuf_el = soup.select_one("a.manufacturers__value")
            if manuf_el:
                manufacturer = manuf_el.get_text(" ", strip=True)

            # Год выпуска - логика из примера
            year = self._extract_year_from_text(soup)

            # Игровые характеристики - логика из примера
            players, play_time, age = self._extract_game_characteristics_from_tags(soup)

            return ProductData(
                title=title,
                url=url,
                price_rub=price_rub,
                manufacturer=manufacturer,
                year=year,
                players=players,
                play_time=play_time,
                age=age,
                description=description,
            )

        except Exception as e:
            self.logger.error(f"Ошибка при извлечении данных товара: {e}")
            return None

    def _extract_price_hobbygames(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлечение цены (логика из примера HobbyGames)"""
        price_sel_candidates = [
            ".product-card-price__current",
            ".product-card-price_current",
            ".product-price__current",
            ".product-price, .price",
        ]
        for sel in price_sel_candidates:
            el = soup.select_one(sel)
            if el:
                price = self._to_int(el.get_text(" ", strip=True))
                if price is not None:
                    return price
        return None

    def _extract_year(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлечение года выпуска (логика из примера)"""
        year_patterns = [r"(\d{4})\s*г", r"год[:\s]*(\d{4})", r"(\d{4})\s*год"]
        page_text = soup.get_text()
        for pattern in year_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                year = int(match.group(1))
                if 1900 <= year <= 2030:  # разумный диапазон годов
                    return year
        return None

    def _extract_game_characteristics(self, soup: BeautifulSoup) -> tuple:
        """Извлечение игровых характеристик (логика из примера)"""
        players = None
        play_time = None
        age = None

        for tag in soup.select(".product-tag"):
            tag_text = tag.get_text(" ", strip=True)

            # Количество игроков
            if "-" in tag_text and tag_text.replace("-", "").replace(" ", "").isdigit():
                if not players:
                    players = self._parse_range(tag_text)

            # Время партии
            if "-" in tag_text and any(char.isdigit() for char in tag_text):
                nums = [int(x) for x in tag_text.split("-") if x.strip().isdigit()]
                if nums and all(n >= 30 for n in nums):  # время обычно от 30+ минут
                    if not play_time:
                        play_time = self._parse_range(tag_text)

            # Возраст
            if "+" in tag_text:
                if not age:
                    age = self._parse_range(tag_text)

        return players, play_time, age

    def _extract_description_hobbygames(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение описания (логика из примера)"""
        desc = soup.select_one("#desc.desc-text")
        if desc:
            parts = [p.get_text(" ", strip=True) for p in desc.select("p")]
            description = "\n\n".join([p for p in parts if p])
            return description[:600] if description else None

        # Резервный поиск
        desc = soup.select_one(".desc-text, .product-description")
        if desc:
            parts = [p.get_text(" ", strip=True) for p in desc.select("p")]
            description = "\n\n".join([p for p in parts if p])
            return description[:600] if description else None

        return None

    def _extract_products_from_category(
        self, soup: BeautifulSoup, limit: int, shop_url: str = None
    ) -> List[ProductData]:
        """Извлечение товаров из категории (логика из примера HobbyGames)"""
        products = []

        if not shop_url:
            self.logger.error("shop_url не может быть пустым")
            return products

        # 1) Современная разметка HobbyGames: ссылки в .product-card-title a
        link_selectors = [
            ".product-card-title a",
            ".product-card__title a",
            "a.catalog-item__title",
            "a.product-item-title",
        ]

        links = []
        for sel in link_selectors:
            links = soup.select(sel)
            if links:
                break

        # 2) Если ничего не нашли — пробуем старые карточки целиком
        if not links:
            product_cards = soup.select(
                '[data-entity="parent-container"], .product-item, .catalog__items .catalog__item, .items .item'
            )
            for card in product_cards:
                link = card.select_one("a[href]")
                if link:
                    links.append(link)

        # Парсим найденные ссылки
        for a in links[:limit]:
            title = (a.get_text(strip=True) if a else None) or ""
            url = (a.get("href") if a else None) or ""

            if not url or not title:
                continue

            if url.startswith("/"):
                url = "https://hobbygames.ru" + url

            # НОВОЕ: Всегда заходим на страницу товара для получения полной информации
            try:
                time.sleep(0.5)  # Задержка между запросами
                product_response = self.session.get(url, timeout=30)
                product_response.raise_for_status()
                product_soup = BeautifulSoup(product_response.content, "lxml")

                # Парсим полную информацию со страницы товара
                full_product = self._extract_product_data(product_soup, url)
                if full_product:
                    products.append(full_product)
                    self.logger.info(f"Успешно спарсил товар: {full_product.title}")
                    continue
            except Exception as e:
                self.logger.warning(f"Не удалось парсить страницу товара {url}: {e}")

            # Если не удалось получить полную информацию, используем базовую с карточки
            card = a.find_parent(class_=lambda c: c and "product-card" in c) or a.parent
            price_rub = None
            if card:
                price_el = card.select_one(
                    '.product-card-price, .product-price, .price, [data-entity="price-current"] .price-value'
                )
                if price_el:
                    price_rub = self._to_int(price_el.get_text(" ", strip=True))

            # Создаем базовый ProductData как fallback
            product = ProductData(
                title=title,
                url=url,
                price_rub=price_rub,
                manufacturer=None,
                year=None,
                players=None,
                play_time=None,
                age=None,
                description=None,
            )
            products.append(product)
            self.logger.warning(f"Использован базовый парсинг для товара: {title}")

        return products

    def _to_int(self, text: str) -> Optional[int]:
        """Конвертация текста в число (из примера)"""
        if text is None:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else None

    def _parse_range(self, text: str) -> Optional[str]:
        """Парсинг диапазона типа '1-2' или '60-120' (из примера)"""
        if not text:
            return None
        cleaned = text.strip()
        cleaned = re.sub(r"[^\d\-\+]", "", cleaned)
        return cleaned if cleaned else None

    def _extract_year_from_text(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлечение года выпуска (логика из примера ghbs)"""
        # Ищем год в тексте страницы
        page_text = soup.get_text()
        year_pattern = r"\b(19|20)\d{2}\b"
        years = re.findall(year_pattern, page_text)

        if years:
            # Берем последний найденный год (обычно это год выпуска)
            return int(max(years))

        return None

    def _extract_game_characteristics_from_tags(self, soup: BeautifulSoup) -> tuple:
        """Извлечение игровых характеристик из тегов (логика из примера ghbs)"""
        players = None
        play_time = None
        age = None

        for tag in soup.select(".product-tag"):
            tag_text = tag.get_text(" ", strip=True)

            # Количество игроков (формат "1-2", "3-4" и т.д.)
            if "-" in tag_text and tag_text.replace("-", "").replace(" ", "").isdigit():
                if not players:  # берем первый найденный
                    players = self._parse_range(tag_text)

            # Время партии (формат "60-120", "30-45" и т.д.)
            if "-" in tag_text and any(char.isdigit() for char in tag_text):
                # Проверяем что это время (большие числа)
                nums = [int(x) for x in tag_text.split("-") if x.strip().isdigit()]
                if nums and all(n >= 30 for n in nums):  # время обычно от 30+ минут
                    if not play_time:  # берем первый найденный
                        play_time = self._parse_range(tag_text)

            # Возраст (формат "14+", "8+", "18+" и т.д.)
            if "+" in tag_text:
                if not age:  # берем первый найденный
                    age = self._parse_range(tag_text)

        return players, play_time, age

    def _parse_range(self, text: str) -> Optional[str]:
        """Парсинг диапазона значений (логика из примера ghbs)"""
        if not text:
            return None

        # Очищаем текст от лишних символов
        cleaned = text.strip()

        # Проверяем формат диапазона
        if "-" in cleaned or "+" in cleaned:
            return cleaned

        return None


# import logging
# import re
# from typing import List, Optional
# from urllib.parse import urljoin

# import requests
# from bs4 import BeautifulSoup

# from shared_models import ProductData


# class BeautifulSoupParser:
#     """Универсальный BeautifulSoup парсер для HTML сайтов"""

#     def __init__(self, base_url: str, max_retries: int = 3):
#         self.base_url = base_url
#         self.max_retries = max_retries
#         self.logger = logging.getLogger(__name__)
#         self.session = requests.Session()
#         self.session.headers.update({
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
#         })

#     def parse_product(self, url: str) -> Optional[ProductData]:
#         """Парсинг одного товара"""
#         try:
#             response = self.session.get(url, timeout=10)
#             response.raise_for_status()

#             soup = BeautifulSoup(response.content, "html.parser")
#             return self._extract_product_data(soup, url)

#         except Exception as e:
#             self.logger.error(f"Ошибка при парсинге {url}: {e}")
#             return None

#     def parse_catalog(self, shop_url: str, limit: int = 100) -> List[ProductData]:
#         """Парсинг каталога магазина"""
#         try:
#             if not shop_url:
#                 self.logger.error("shop_url не может быть пустым")
#                 return []

#             # Используем переданный shop_url
#             response = self.session.get(shop_url, timeout=10)
#             response.raise_for_status()

#             soup = BeautifulSoup(response.content, "html.parser")
#             return self._extract_products_from_category(soup, limit, shop_url)
#         except Exception as e:
#             self.logger.error(f"Ошибка при парсинге каталога: {e}")
#             return []

#     def _extract_product_data(
#         self, soup: BeautifulSoup, url: str
#     ) -> Optional[ProductData]:
#         """Извлечение данных товара со страницы"""
#         try:
#             # Название
#             title_element = soup.find("h1")
#             title = title_element.get_text(strip=True) if title_element else ""

#             if not title:
#                 return None

#             # Цена
#             price_rub = self._extract_price(soup)

#             # Характеристики
#             characteristics = self._extract_characteristics(soup)

#             # Описание
#             description = self._extract_description(soup)

#             return ProductData(
#                 title=title,
#                 url=url,
#                 price_rub=price_rub,
#                 manufacturer=characteristics.get("manufacturer"),
#                 year=characteristics.get("year"),
#                 players=characteristics.get("players"),
#                 play_time=characteristics.get("play_time"),
#                 age=characteristics.get("age"),
#                 description=description,
#             )

#         except Exception as e:
#             self.logger.error(f"Ошибка при извлечении данных товара: {e}")
#             return None

#     def _extract_price(self, soup: BeautifulSoup) -> Optional[int]:
#         """Извлечение цены товара"""
#         price_selectors = [
#             ".price",
#             ".cost",
#             ".amount",
#             ".product-price",
#             "[data-price]",
#             ".current-price",
#             ".main-price",
#         ]

#         for selector in price_selectors:
#             price_element = soup.select_one(selector)
#             if price_element:
#                 price_text = price_element.get_text(strip=True)
#                 return self._extract_numbers_from_text(price_text)

#         return None

#     def _extract_characteristics(self, soup: BeautifulSoup) -> dict:
#         """Извлечение характеристик товара"""
#         characteristics = {}

#         # Ищем таблицы с характеристиками
#         tables = soup.find_all("table")
#         for table in tables:
#             rows = table.find_all("tr")
#             for row in rows:
#                 cells = row.find_all(["td", "th"])
#                 if len(cells) >= 2:
#                     key = cells[0].get_text(strip=True).lower()
#                     value = cells[1].get_text(strip=True)

#                     if "производитель" in key or "издатель" in key:
#                         characteristics["manufacturer"] = value
#                     elif "год" in key:
#                         year_match = re.search(r"(\d{4})", value)
#                         if year_match:
#                             characteristics["year"] = int(year_match.group(1))
#                     elif "игрок" in key and "возраст" not in key:
#                         characteristics["players"] = value
#                     elif "время" in key or "минут" in key:
#                         characteristics["play_time"] = value
#                     elif "возраст" in key:
#                         characteristics["age"] = value

#         return characteristics

#     def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
#         """Извлечение описания товара"""
#         desc_selectors = [
#             ".description",
#             ".product-description",
#             ".about",
#             ".content",
#             ".text",
#             ".game-description",
#         ]

#         for selector in desc_selectors:
#             desc_element = soup.select_one(selector)
#             if desc_element:
#                 description = desc_element.get_text(strip=True)
#                 if len(description) > 100:
#                     return description[:600]  # Ограничиваем длину

#         return None

#     def _extract_numbers_from_text(self, text: str) -> Optional[int]:
#         """Извлечение первого числа из текста"""
#         numbers = re.findall(r"\d+", text.replace(" ", ""))
#         return int(numbers[0]) if numbers else None

#     def _extract_products_from_category(
#         self, soup: BeautifulSoup, limit: int, shop_url: str = None
#     ) -> List[ProductData]:
#         """Извлечение товаров из категории"""
#         products = []

#         if not shop_url:
#             self.logger.error("shop_url не может быть пустым")
#             return products

#         # Ищем ссылки на товары
#         product_links = []
#         links = soup.find_all("a", href=True)

#         for link in links:
#             href = link["href"]
#             # Более гибкий поиск ссылок на товары
#             if any(
#                 pattern in href
#                 for pattern in ["/product/", "/game/", "/nastolnaya-igra-", "/igra-"]
#             ):
#                 full_url = urljoin(shop_url, href)
#                 if full_url not in product_links:
#                     product_links.append(full_url)

#         # Парсим товары
#         for url in product_links[:limit]:
#             product = self.parse_product(url)
#             if product:
#                 products.append(product)

#         return products
