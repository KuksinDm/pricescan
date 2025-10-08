from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def alerts_kb(
    items: list[dict], selected: set[int], prev_off: int | None, next_off: int | None
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for alert_item in items:
        mark = "✅ " if alert_item["id"] in selected else ""

        threshold_price = alert_item.get("threshold_price")
        currency = alert_item.get("currency") or ""
        price_text = (
            f" ≤ {threshold_price} {currency}" if threshold_price is not None else ""
        )

        status = "вкл" if alert_item.get("is_active") else "выкл"

        title = alert_item.get("product_title") or str(alert_item.get("product"))

        button_text = f"{mark}{title}{price_text} — {status}"
        if len(button_text) > 60:
            button_text = button_text[:57] + "..."

        rows.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"alert-sel:{alert_item['id']}",
            )
        ])

    management_buttons = [
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
    rows.extend(management_buttons)

    navigation_buttons = []
    if prev_off is not None:
        navigation_buttons.append(
            InlineKeyboardButton(text="◀︎", callback_data=f"alert-page:{prev_off}")
        )
    if next_off is not None:
        navigation_buttons.append(
            InlineKeyboardButton(text="▶︎", callback_data=f"alert-page:{next_off}")
        )

    if navigation_buttons:
        rows.append(navigation_buttons)

    return InlineKeyboardMarkup(inline_keyboard=rows)
