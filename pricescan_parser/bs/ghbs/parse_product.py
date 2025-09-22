from __future__ import annotations

from typing import Dict

from bs4 import BeautifulSoup

from .parse_category import _to_int


def _parse_range(text: str) -> str:
    """Парсит диапазон типа '1-2' или '60-120'"""
    if not text:
        return None
    cleaned = text.strip()
    # Убираем лишние символы, оставляем цифры, дефисы, плюсы
    import re

    cleaned = re.sub(r"[^\d\-\+]", "", cleaned)
    return cleaned if cleaned else None


def parse_product_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "lxml")

    # Название
    title = None
    h1 = soup.select_one(".product-info__main h1, h1")
    if h1:
        title = h1.get_text(" ", strip=True)

    # Цена
    price = None
    price_sel_candidates = [
        ".product-card-price__current",
        ".product-card-price_current",
        ".product-price__current",
        ".product-price, .price",
    ]
    for sel in price_sel_candidates:
        el = soup.select_one(sel)
        if el:
            price = _to_int(el.get_text(" ", strip=True))
            if price is not None:
                break

    # Описание
    description = None
    # Ищем контейнер с описанием (не заголовок "Описание")
    desc = soup.select_one("#desc.desc-text")
    if desc:
        # Собираем абзацы из описания
        parts = [p.get_text(" ", strip=True) for p in desc.select("p")]
        description = "\n\n".join([p for p in parts if p])
    else:
        # Резервный поиск
        desc = soup.select_one(".desc-text, .product-description")
        if desc:
            parts = [p.get_text(" ", strip=True) for p in desc.select("p")]
            description = "\n\n".join([p for p in parts if p])

    # Производитель
    manufacturer = None
    manuf_el = soup.select_one("a.manufacturers__value")
    if manuf_el:
        manufacturer = manuf_el.get_text(" ", strip=True)

    # Год выпуска (ищем в другом месте, не в производителе)
    year = None
    # Ищем год в тексте страницы или специальных полях
    year_patterns = [r"(\d{4})\s*г", r"год[:\s]*(\d{4})", r"(\d{4})\s*год"]
    import re

    page_text = soup.get_text()
    for pattern in year_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:  # разумный диапазон годов
                break

    # Парсим теги: игроки, время, возраст
    players = None
    play_time = None
    age = None

    for tag in soup.select(".product-tag"):
        tag_text = tag.get_text(" ", strip=True)

        # Количество игроков (формат "1-2", "3-4" и т.д.)
        if "-" in tag_text and tag_text.replace("-", "").replace(" ", "").isdigit():
            if not players:  # берем первый найденный
                players = _parse_range(tag_text)

        # Время партии (формат "60-120", "30-45" и т.д.)
        if "-" in tag_text and any(char.isdigit() for char in tag_text):
            # Проверяем что это время (большие числа)
            nums = [int(x) for x in tag_text.split("-") if x.strip().isdigit()]
            if nums and all(n >= 30 for n in nums):  # время обычно от 30+ минут
                if not play_time:  # берем первый найденный
                    play_time = _parse_range(tag_text)

        # Возраст (формат "14+", "8+", "18+" и т.д.)
        if "+" in tag_text:
            if not age:  # берем первый найденный
                age = _parse_range(tag_text)

    return {
        "title": title,
        "url": url,
        "price_rub": price,
        "manufacturer": manufacturer,
        "year": year,
        "players": players,
        "play_time": play_time,
        "age": age,
        "description": description,
    }
