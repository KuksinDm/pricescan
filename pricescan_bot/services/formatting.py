from typing import Any, Dict


def fmt_dt_iso(ts: str | None) -> str:
    """Форматирует ISO дату/время, возвращая только дату"""
    if not ts:
        return "-"
    ts = ts.replace("Z", "+00:00")
    return ts[:10]


def format_offer_text_no_description(offer: Dict[str, Any]) -> str:
    """Форматирует текст товара без описания для отображения в боте"""
    # Обрабатываем множественные издатели и категории
    publishers = offer.get("product_publishers", [])
    categories = offer.get("product_categories", [])

    publishers_str = ", ".join(publishers) if publishers else "Неизвестно"
    categories_str = ", ".join(categories) if categories else "Неизвестно"

    return (
        f"Игра: {offer['product_title']}\n"
        f"Издатель: {publishers_str}\n"
        f"Категория: {categories_str}\n"
        f"Игроки: {offer.get('min_players') or '?'}–{offer.get('max_players') or '?'} | "
        f"Время: {offer.get('playtime_min') or '?'} мин | Возраст: {offer.get('min_age') or '?'}+\n"
        f"Цена: {offer['price']} {offer['currency']} | Магазин: {offer['shop']['name']}"
    )
