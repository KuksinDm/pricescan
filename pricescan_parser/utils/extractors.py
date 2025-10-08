import re
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup
from constants import EXCLUDED_CATEGORIES, HOBBYGAMES_SELECTORS


class DataExtractor:
    """Утилиты для извлечения данных из HTML - убираем дублирование"""

    @staticmethod
    def extract_by_selectors(
        soup: BeautifulSoup, selectors: List[str], single: bool = True
    ) -> Optional[str]:
        """Универсальный метод извлечения данных по селекторам"""
        for selector in selectors:
            if single:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(" ", strip=True)
            else:
                elements = soup.select(selector)
                if elements:
                    return [el.get_text(" ", strip=True) for el in elements]
        return None if single else []

    @staticmethod
    def extract_title(soup: BeautifulSoup) -> Optional[str]:
        """Извлечение названия товара"""
        return DataExtractor.extract_by_selectors(soup, HOBBYGAMES_SELECTORS["title"])

    @staticmethod
    def extract_price(soup: BeautifulSoup) -> Optional[int]:
        """Извлечение цены товара"""
        price_text = DataExtractor.extract_by_selectors(
            soup, HOBBYGAMES_SELECTORS["price"]
        )
        return DataExtractor._to_int(price_text) if price_text else None

    @staticmethod
    def extract_manufacturers(soup: BeautifulSoup) -> List[str]:
        """Извлечение производителей"""
        manufacturers = []

        for selector in HOBBYGAMES_SELECTORS["manufacturers"]:
            elements = soup.select(selector)
            for element in elements:
                manufacturer = element.get_text(" ", strip=True)
                if manufacturer and manufacturer not in manufacturers:
                    manufacturers.append(manufacturer)

        return manufacturers

    @staticmethod
    def extract_categories(soup: BeautifulSoup) -> List[str]:
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

    @staticmethod
    def extract_game_characteristics(
        soup: BeautifulSoup,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Извлечение игровых характеристик"""
        players = DataExtractor._extract_players_from_attrs(soup)
        play_time = None
        age = None

        for selector in HOBBYGAMES_SELECTORS["game_tags"]:
            tags = soup.select(selector)

            for tag in tags:
                tag_text = tag.get_text(" ", strip=True)

                # Количество игроков
                if (
                    "-" in tag_text
                    and tag_text.replace("-", "").replace(" ", "").isdigit()
                    and not players
                ):
                    players = DataExtractor._parse_range(tag_text)

                # Время партии
                if (
                    "-" in tag_text
                    and any(char.isdigit() for char in tag_text)
                    and not play_time
                ):
                    nums = [int(x) for x in tag_text.split("-") if x.strip().isdigit()]
                    if nums:
                        play_time = DataExtractor._parse_range(tag_text)

                # Возраст
                if "+" in tag_text and not age:
                    age = DataExtractor._parse_range(tag_text)

        return players, play_time, age

    @staticmethod
    def find_product_links(soup: BeautifulSoup) -> List:
        """Поиск ссылок на товары"""
        links = []

        for selector in HOBBYGAMES_SELECTORS["product_links"]:
            found_links = soup.select(selector)
            if found_links:
                links = found_links
                break

        if not links:
            product_cards = soup.select(
                ", ".join(HOBBYGAMES_SELECTORS["product_cards"])
            )
            for card in product_cards:
                link = card.select_one("a[href]")
                if link:
                    links.append(link)

        return links

    @staticmethod
    def _extract_players_from_attrs(soup: BeautifulSoup) -> Optional[str]:
        """Ищет количество игроков в таблицах атрибутов"""
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
                return DataExtractor._parse_range(val)
        return None

    @staticmethod
    def _to_int(text: str) -> Optional[int]:
        """Конвертация текста в число"""
        if text is None:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else None

    @staticmethod
    def _parse_range(text: str) -> Optional[str]:
        """Парсинг диапазона значений"""
        if not text:
            return None
        s = text.strip().replace("–", "-").replace("—", "-")
        cleaned = re.sub(r"[^\d\-\+]", "", s)
        return cleaned if cleaned else None

    @staticmethod
    def extract_price_from_element(element) -> Optional[int]:
        """Извлечение цены из конкретного элемента (для карточек товаров)"""
        for selector in HOBBYGAMES_SELECTORS["price"]:
            price_el = element.select_one(selector)
            if price_el:
                price_text = price_el.get_text(" ", strip=True)
                price = DataExtractor._to_int(price_text)
                if price is not None:
                    return price
        return None
