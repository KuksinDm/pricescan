# pricescan_bot/keyboards/favorites.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def favorites_kb(
    items: list[dict], selected: set[int], prev_off: int | None, next_off: int | None
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for it in items:
        mark = "✅ " if it["id"] in selected else ""
        title = it.get("product_title") or str(it.get("product"))
        rows.append([
            InlineKeyboardButton(
                text=f"{mark}{title}", callback_data=f"fav-sel:{it['id']}"
            )
        ])
        pid = it.get("product")
        if pid is not None:
            url = it.get("first_offer_url")
            rows.append([
                InlineKeyboardButton(text="Обновить", callback_data=f"refresh:{pid}"),
                InlineKeyboardButton(text="Открыть", url=url)
                if url
                else InlineKeyboardButton(
                    text="Открыть", callback_data=f"offers:{pid}"
                ),
            ])
    rows += [
        [
            InlineKeyboardButton(
                text="Удалить выбранные", callback_data="fav-del-selected"
            )
        ]
    ]
    nav = []
    if prev_off is not None:
        nav.append(InlineKeyboardButton(text="◀︎", callback_data=f"fav-page:{prev_off}"))
    if next_off is not None:
        nav.append(InlineKeyboardButton(text="▶︎", callback_data=f"fav-page:{next_off}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)
