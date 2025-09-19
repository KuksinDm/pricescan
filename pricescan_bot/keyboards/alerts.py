# pricescan_bot/keyboards/alerts.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def alerts_kb(
    items: list[dict], selected: set[int], prev_off: int | None, next_off: int | None
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for it in items:
        mark = "✅ " if it["id"] in selected else ""
        thr = it.get("threshold_price")
        cur = it.get("currency") or ""
        thr_part = f" ≤ {thr} {cur}" if thr is not None else ""
        status = "вкл" if it.get("is_active") else "выкл"
        title = it.get("product_title") or str(it.get("product"))
        rows.append([
            InlineKeyboardButton(
                text=f"{mark}{title}{thr_part} — {status}",
                callback_data=f"alert-sel:{it['id']}",
            )
        ])
    rows += [
        [
            InlineKeyboardButton(
                text="Включить выбранные", callback_data="alert-on-selected"
            ),
            InlineKeyboardButton(
                text="Выключить выбранные", callback_data="alert-off-selected"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Удалить выбранные", callback_data="alert-del-selected"
            )
        ],
        [
            InlineKeyboardButton(
                text="Изменить цену выбранных", callback_data="alert-edit-selected"
            )
        ],
    ]
    nav = []
    if prev_off is not None:
        nav.append(
            InlineKeyboardButton(text="◀︎", callback_data=f"alert-page:{prev_off}")
        )
    if next_off is not None:
        nav.append(
            InlineKeyboardButton(text="▶︎", callback_data=f"alert-page:{next_off}")
        )
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)
