from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from .texts import ALERTS_BTN, FAV_BTN, HELP_BTN, HISTORY_BTN, SEARCH_BTN


def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text=SEARCH_BTN), width=1)
    kb.row(KeyboardButton(text=FAV_BTN), KeyboardButton(text=ALERTS_BTN), width=2)
    kb.row(KeyboardButton(text=HISTORY_BTN), KeyboardButton(text=HELP_BTN), width=2)
    return kb.as_markup(
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Введите название игры или нажмите «Найти»",
    )


def offer_actions_kb(product_id: int, url: str, currency: str):
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


# Reply-клавиатуры для режимов выбора
FAV_DELETE_SELECTED = "Удалить выбранные"
ALERT_ON_SELECTED = "Включить выбранные"
ALERT_OFF_SELECTED = "Выключить выбранные"
BACK_BTN = "Назад"


def fav_actions_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text=SEARCH_BTN), width=1)
    kb.row(KeyboardButton(text=FAV_DELETE_SELECTED), width=1)
    kb.row(KeyboardButton(text=BACK_BTN), width=1)
    return kb.as_markup(resize_keyboard=True, is_persistent=True)


def alert_actions_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text=SEARCH_BTN), width=1)
    kb.row(
        KeyboardButton(text=ALERT_ON_SELECTED),
        KeyboardButton(text=ALERT_OFF_SELECTED),
        width=2,
    )
    kb.row(KeyboardButton(text=FAV_DELETE_SELECTED), width=1)
    kb.row(KeyboardButton(text=BACK_BTN), width=1)
    return kb.as_markup(resize_keyboard=True, is_persistent=True)
