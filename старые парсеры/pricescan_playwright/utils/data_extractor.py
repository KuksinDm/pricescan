# pricescan_playwright/utils/data_extractor.py
import html
import re
from typing import Any, Optional

from constants import EXCLUDED_CATEGORIES
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
    def normalize_title(raw: str | None) -> str | None:
        """Нормализация заголовка"""
        if not raw:
            return None
        s = html.unescape(str(raw)).strip()
        m = re.search(r'^\s*Купить\s+[«""]?(.+?)[»""]?\s+в\s+Мосигре', s, flags=re.I)
        if m:
            return m.group(1).strip(" \"'«»").strip()
        s = re.sub(r"\s+[|–—-]\s*Мосигра.*$", "", s, flags=re.I)
        s = re.sub(r"\s+в\s+Мосигре.*$", "", s, flags=re.I)
        m2 = re.search(r'^\s*Купить\s+[«""]?(.+?)[»""]?\s*$', s, flags=re.I)
        if m2:
            s = m2.group(1)
        return s.strip(" \"'«»").strip() or None

    async def extract_title(self, page: Page) -> Optional[str]:
        """Извлечение заголовка товара"""
        try:
            t = await page.eval_on_selector(
                'meta[property="og:title"], meta[name="og:title"]',
                "el => el && (el.getAttribute('content') || el.content)",
            )
            t = self.normalize_title(t)
            if t:
                return t
        except Exception:
            pass

        for sel in ["h1", ".card_title", ".ProductCard__title", '[itemprop="name"]']:
            try:
                txt = await page.locator(sel).first.text_content(timeout=1000)
                txt = self.normalize_title(txt)
                if txt:
                    return txt
            except Exception:
                continue
        return None

    async def extract_price(self, page: Page) -> Optional[int]:
        """Извлечение цены товара"""
        try:
            price_meta = await page.eval_on_selector(
                'meta[itemprop="price"]',
                "el => el && (el.getAttribute('content') || el.content)",
            )
            p = self.normalize_price(price_meta)
            if p:
                return p
        except Exception:
            pass

        for sel in (
            "b.h1",
            ".h1",
            ".price",
            ".price__current",
            ".ProductCard__price-current",
            ".product-price",
            ".amount",
            ".cost",
            ".buy-price",
            ".main-price",
        ):
            try:
                txt = await page.locator(sel).first.text_content(timeout=800)
                p = self.normalize_price(txt)
                if p:
                    return p
            except Exception:
                continue
        return None

    async def extract_attributes(self, page: Page) -> dict[str, Any]:
        """Извлечение атрибутов товара"""
        try:
            return await page.evaluate("""
() => {
  const out = {};
  const sect = document.querySelector('section#attributes');
  const table = sect ? sect.querySelector('table') : document.querySelector('#attributes table');
  if (!table) return out;
  const rows = Array.from(table.querySelectorAll('tr'));
  for (const tr of rows) {
    const tds = tr.querySelectorAll('td');
    if (tds.length < 2) continue;
    const k = tds[0].textContent?.trim() || '';
    const td2 = tds[1];
    let v = td2.textContent?.trim() || '';
    const links = Array.from(td2.querySelectorAll('a')).map(a => a.textContent?.trim()).filter(Boolean);
    out[k] = links.length ? links : v;
  }
  return out;
}
""")
        except Exception:
            return {}

    async def extract_categories(self, page: Page) -> list[str]:
        """Извлечение категорий товара"""
        try:
            cats = await page.eval_on_selector_all(
                "article.categories a.categories_link, .categories a.categories_link, a.categories_link",
                "els => els.map(e => e.textContent && e.textContent.trim()).filter(Boolean)",
            )
            if not cats:
                cats = await page.eval_on_selector_all(
                    ".categories a, .breadcrumbs a, .breadcrumb a",
                    "els => els.map(e => e.textContent && e.textContent.trim()).filter(Boolean)",
                )
        except Exception:
            cats = []

        result, seen = [], set()
        for c in cats or []:
            if c in EXCLUDED_CATEGORIES or c in seen:
                continue
            seen.add(c)
            result.append(c)
        return result
