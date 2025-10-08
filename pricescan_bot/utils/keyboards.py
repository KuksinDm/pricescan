from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from .texts import ALERTS_BTN, DISCOUNTS_BTN, FAV_BTN, HELP_BTN, SEARCH_BTN


def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text=SEARCH_BTN), width=1)
    kb.row(KeyboardButton(text=FAV_BTN), KeyboardButton(text=ALERTS_BTN), width=2)
    kb.row(KeyboardButton(text=DISCOUNTS_BTN), KeyboardButton(text=HELP_BTN), width=2)
    return kb.as_markup(
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Введите название игры или нажмите «Найти»",
    )


def offer_actions_kb(product_id: int, url: str, currency: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Обновить цены", callback_data=f"refresh:{product_id}"
                ),
                InlineKeyboardButton(
                    text="Все предложения", callback_data=f"offers:{product_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="В избранное", callback_data=f"fav-add:{product_id}"
                ),
                InlineKeyboardButton(
                    text="Создать алерт",
                    callback_data=f"alert-new:{product_id}:{currency}",
                ),
            ],
            [InlineKeyboardButton(text="Открыть в магазине", url=url)],
        ]
    )
