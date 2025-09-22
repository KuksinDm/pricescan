from __future__ import annotations

from typing import Dict, List

from bs4 import BeautifulSoup


def _to_int(text: str) -> int | None:
    if text is None:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def _to_float(text: str) -> float | None:
    if text is None:
        return None
    cleaned = text.replace(",", ".")
    num_chars = [c for c in cleaned if c.isdigit() or c in ".-"]
    try:
        return float("".join(num_chars)) if num_chars else None
    except ValueError:
        return None


def parse_category_page(html: str, page_url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")

    items: List[Dict] = []

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

    for a in links:
        title = (a.get_text(strip=True) if a else None) or ""
        url = (a.get("href") if a else None) or ""

        card = a.find_parent(class_=lambda c: c and "product-card" in c) or a.parent

        # Картинка рядом с карточкой
        image_url = None
        if card:
            img_el = card.select_one(
                "img, .product-item-image-original, .catalog-item__image img"
            )
            if img_el:
                image_url = img_el.get("data-src") or img_el.get("src")

        # Цена
        price_rub = None
        if card:
            price_el = card.select_one(
                '.product-card-price, .product-price, .price, [data-entity="price-current"] .price-value'
            )
            if price_el:
                price_rub = _to_int(price_el.get_text(" ", strip=True))

        if not url:
            continue
        if url.startswith("/"):
            url = "https://hobbygames.ru" + url

        items.append({
            "title": title,
            "url": url,
            "price_rub": price_rub,
            "source_page": page_url,
        })

    return items
