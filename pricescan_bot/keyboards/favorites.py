from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def favorites_kb(
    items: list[dict], selected: set[int], prev_off: int | None, next_off: int | None
) -> InlineKeyboardMarkup:
    """Создает клавиатуру для списка избранных товаров с пагинацией и множественным выбором"""
    rows: list[list[InlineKeyboardButton]] = []

    # Создаем кнопки для каждого избранного товара
    for favorite_item in items:
        # Маркер выбранного элемента
        mark = "✅ " if favorite_item["id"] in selected else ""

        # Название товара
        title = favorite_item.get("product_title") or str(favorite_item.get("product"))

        # Ограничиваем длину текста кнопки
        button_text = f"{mark}{title}"
        if len(button_text) > 60:  # Telegram ограничение
            button_text = button_text[:57] + "..."

        # Кнопка выбора товара
        rows.append([
            InlineKeyboardButton(
                text=button_text, callback_data=f"fav-sel:{favorite_item['id']}"
            )
        ])

        # Кнопки действий для товара
        product_id = favorite_item.get("product")
        if product_id is not None:
            first_offer_url = favorite_item.get("first_offer_url")

            # Создаем кнопку "Открыть" - либо URL, либо список предложений
            if first_offer_url:
                open_button = InlineKeyboardButton(text="Открыть", url=first_offer_url)
            else:
                open_button = InlineKeyboardButton(
                    text="Открыть", callback_data=f"offers:{product_id}"
                )

            rows.append([
                InlineKeyboardButton(
                    text="Обновить", callback_data=f"refresh:{product_id}"
                ),
                open_button,
            ])

    # Кнопка удаления выбранных элементов
    management_buttons = [
        [
            InlineKeyboardButton(
                text="Удалить выбранные", callback_data="fav-del-selected"
            )
        ]
    ]
    rows.extend(management_buttons)

    # Кнопки навигации
    navigation_buttons = []
    if prev_off is not None:
        navigation_buttons.append(
            InlineKeyboardButton(text="◀︎", callback_data=f"fav-page:{prev_off}")
        )
    if next_off is not None:
        navigation_buttons.append(
            InlineKeyboardButton(text="▶︎", callback_data=f"fav-page:{next_off}")
        )

    if navigation_buttons:
        rows.append(navigation_buttons)

    return InlineKeyboardMarkup(inline_keyboard=rows)
