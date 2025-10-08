# pricescan_playwright/utils/data_extractor.py
import html
import re
from typing import Any, List, Optional

from constants import (
    CATEGORY_SELECTORS,
    EXCLUDED_CATEGORIES,
    PRICE_SELECTORS,
    TITLE_SELECTORS,
)
from playwright.async_api import Page


class PlaywrightDataExtractor:
    """Извлекатель данных из Playwright страниц"""

    @staticmethod
    def normalize_price(text: Optional[str]) -> Optional[int]:
        """Нормализация цены"""
        if not text:
            return None
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else None

    @staticmethod
    def normalize_title(raw_title: str | None) -> str | None:
        """Нормализация заголовка"""
        if not raw_title:
            return None
        clean_title = html.unescape(str(raw_title)).strip()

        # Убираем "Купить ... в Мосигре"
        buy_pattern = re.search(
            r'^\s*Купить\s+[«""]?(.+?)[»""]?\s+в\s+Мосигре', clean_title, flags=re.I
        )
        if buy_pattern:
            return buy_pattern.group(1).strip(" \"'«»").strip()

        # Убираем суффиксы Мосигры
        clean_title = re.sub(r"\s+[|–—-]\s*Мосигра.*$", "", clean_title, flags=re.I)
        clean_title = re.sub(r"\s+в\s+Мосигре.*$", "", clean_title, flags=re.I)

        # Убираем "Купить ..."
        buy_only_pattern = re.search(
            r'^\s*Купить\s+[«""]?(.+?)[»""]?\s*$', clean_title, flags=re.I
        )
        if buy_only_pattern:
            clean_title = buy_only_pattern.group(1)

        return clean_title.strip(" \"'«»").strip() or None

    async def extract_title(self, page: Page) -> Optional[str]:
        """Извлечение заголовка товара"""
        try:
            meta_title = await page.eval_on_selector(
                'meta[property="og:title"], meta[name="og:title"]',
                "el => el && (el.getAttribute('content') || el.content)",
            )
            normalized_title = self.normalize_title(meta_title)
            if normalized_title:
                return normalized_title
        except Exception:
            pass

        for selector in TITLE_SELECTORS:
            try:
                title_text = await page.locator(selector).first.text_content(
                    timeout=1000
                )
                normalized_title = self.normalize_title(title_text)
                if normalized_title:
                    return normalized_title
            except Exception:
                continue
        return None

    async def extract_price(self, page: Page) -> Optional[int]:
        """Извлечение цены товара"""
        try:
            meta_price = await page.eval_on_selector(
                'meta[itemprop="price"]',
                "el => el && (el.getAttribute('content') || el.content)",
            )
            normalized_price = self.normalize_price(meta_price)
            if normalized_price:
                return normalized_price
        except Exception:
            pass

        for selector in PRICE_SELECTORS:
            try:
                price_text = await page.locator(selector).first.text_content(
                    timeout=800
                )
                normalized_price = self.normalize_price(price_text)
                if normalized_price:
                    return normalized_price
            except Exception:
                continue
        return None

    async def extract_attributes(self, page: Page) -> dict[str, Any]:
        """Извлечение атрибутов товара"""
        try:
            return await page.evaluate("""
() => {
  const attributes = {};
  const attributes_section = document.querySelector('section#attributes');
  const attributes_table = attributes_section ? attributes_section.querySelector('table') : document.querySelector('#attributes table');
  if (!attributes_table) return attributes;
  const table_rows = Array.from(attributes_table.querySelectorAll('tr'));
  for (const table_row of table_rows) {
    const table_cells = table_row.querySelectorAll('td');
    if (table_cells.length < 2) continue;
    const key = table_cells[0].textContent?.trim() || '';
    const value_cell = table_cells[1];
    let value = value_cell.textContent?.trim() || '';
    const cell_links = Array.from(value_cell.querySelectorAll('a')).map(link => link.textContent?.trim()).filter(Boolean);
    attributes[key] = cell_links.length ? cell_links : value;
  }
  return attributes;
}
""")
        except Exception:
            return {}

    async def extract_categories(self, page: Page) -> list[str]:
        """Извлечение категорий товара"""
        try:
            categories = await page.eval_on_selector_all(
                CATEGORY_SELECTORS[0],
                "elements => elements.map(el => el.textContent && el.textContent.trim()).filter(Boolean)",
            )
            if not categories:
                categories = await page.eval_on_selector_all(
                    CATEGORY_SELECTORS[1],
                    "elements => elements.map(el => el.textContent && el.textContent.trim()).filter(Boolean)",
                )
        except Exception:
            categories = []

        result_categories, seen_categories = [], set()
        for category in categories or []:
            if category in EXCLUDED_CATEGORIES or category in seen_categories:
                continue
            seen_categories.add(category)
            result_categories.append(category)
        return result_categories

    def extract_manufacturers(self, attributes: dict) -> List[str]:
        """Извлечение производителей из атрибутов"""
        manufacturers: List[str] = []
        producer_raw = self._pick_attr(
            attributes, ["Производитель", re.compile(r"производител", re.I)]
        )

        if isinstance(producer_raw, list):
            manufacturers = [producer for producer in producer_raw if producer]
        elif isinstance(producer_raw, str) and producer_raw.strip():
            manufacturers = [
                producer.strip()
                for producer in producer_raw.split(",")
                if producer.strip()
            ]

        return manufacturers

    def extract_players(self, attributes: dict) -> Optional[str]:
        """Извлечение количества игроков"""
        for key, value in attributes.items():
            normalized_key = str(key).strip().lower()
            if "возраст" in normalized_key:  # игнорируем "Возраст игроков"
                continue
            if normalized_key in (
                "количество игроков",
                "игроков",
                "число игроков",
            ) or re.search(r"\bигрок", normalized_key):
                return self._norm_players(value)
        return None

    def extract_play_time(self, attributes: dict) -> Optional[str]:
        """Извлечение времени игры"""
        play_time = self._pick_attr(
            attributes,
            [
                "Время игры",
                "Продолжительность игры",
                re.compile(r"время.*игр", re.I),
            ],
        )
        return str(play_time).strip() if play_time else None

    def extract_age(self, attributes: dict) -> Optional[str]:
        """Извлечение возрастных ограничений"""
        age_value = self._pick_attr(
            attributes,
            [
                "Возраст игроков",
                "Возраст",
                "Возраст игрока",
                "Возрастные ограничения",
                re.compile(r"возраст", re.I),
            ],
        )
        return self._normalize_age(age_value)

    def _pick_attr(self, attributes: dict, candidates: list) -> str | list | None:
        """Поиск атрибута по кандидатам"""
        if not attributes:
            return None
        for key, value in attributes.items():
            normalized_key = str(key).strip().lower()
            for candidate in candidates:
                if isinstance(candidate, str) and normalized_key == candidate.lower():
                    return value
                if hasattr(candidate, "search") and candidate.search(normalized_key):
                    return value
        return None

    def _normalize_age(self, age_value: str | list | None) -> str | None:
        """Нормализация возраста"""
        if age_value is None:
            return None
        if isinstance(age_value, list):
            age_value = ", ".join([str(item) for item in age_value if item])
        age_string = str(age_value).strip()
        age_match = re.search(
            r"(\d+)\s*\+|от\s*(\d+)\s*лет|(\d+)\s*лет", age_string, flags=re.I
        )
        if age_match:
            for group in age_match.groups():
                if group:
                    return f"{group}+"
        return age_string or None

    def _norm_players(self, players_value) -> Optional[str]:
        """Нормализация количества игроков"""
        if players_value is None:
            return None
        if isinstance(players_value, list):
            players_value = " ".join(str(item) for item in players_value if item)
        players_string = (
            str(players_value).strip().lower().replace("–", "-").replace("—", "-")
        )

        # Поиск диапазона "от X до Y" или "X-Y"
        range_match = re.search(
            r"от\s*(\d+)\s*до\s*(\d+)", players_string
        ) or re.search(r"(\d+)\s*-\s*(\d+)", players_string)
        if range_match:
            return f"{range_match.group(1)}-{range_match.group(2)}"

        # Поиск "X+" формата
        plus_match = re.search(r"(\d+)\s*\+", players_string)
        if plus_match:
            return f"{plus_match.group(1)}-{plus_match.group(1)}"

        # Поиск просто числа
        number_match = re.search(r"\b(\d+)\b", players_string)
        return number_match.group(1) if number_match else None
