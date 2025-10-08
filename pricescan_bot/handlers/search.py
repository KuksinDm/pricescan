import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..constants import DEFAULT_OFFERS_LIMIT, MAX_SEARCH_RESULTS
from ..services.formatting import format_offer_text_no_description
from ..services.state import set_wait_mode
from ..utils.auth import ensure_jwt
from ..utils.keyboards import offer_actions_kb
from ..utils.parsers import (
    parse_alert_new_data,
    parse_callback_product_id,
)
from ..utils.texts import SEARCH_BTN, is_button_text

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == SEARCH_BTN)
async def ask_search_query(message: Message):
    """Обработчик кнопки 'Поиск' - запрашивает поисковый запрос"""
    await message.answer("Введите название игры и отправьте сообщение.")


@router.message(
    F.text
    & ~F.text.startswith("/")
    & ~F.text.startswith("fav-")
    & ~F.text.startswith("alert-")
    & ~F.text.func(is_button_text)
    & ~F.text.regexp(r"^\d+[\.,]?\d*$")
)
async def do_search(message: Message, container):
    """Обработчик поиска игр - выполняет поиск и показывает результаты"""
    query = (message.text or "").strip()

    if not query:
        return await message.answer("Пустой запрос. Введите название игры.")

    try:
        await ensure_jwt(message, container.api_client)
    except Exception:
        return await message.answer("Ошибка авторизации. Попробуйте позже.")

    try:
        offers = await container.api_client.get_cheapest(query)
    except Exception:
        logger.exception("Search failed for query: %s", query)
        return await message.answer("Сервис временно недоступен. Попробуйте позже.")

    if not offers:
        return await message.answer("Ничего не нашлось")

    for offer in offers[:MAX_SEARCH_RESULTS]:
        text = format_offer_text_no_description(offer)

        keyboard = offer_actions_kb(offer["product"], offer["url"], offer["currency"])

        await message.answer(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


@router.callback_query(F.data.startswith("refresh:"))
async def cb_refresh_product(cb: CallbackQuery, container):
    try:
        product_id = parse_callback_product_id(cb.data)
    except ValueError:
        return await cb.answer("Ошибка в данных товара", show_alert=True)

    try:
        success = await container.api_client.refresh_product(
            product_id, telegram_id=cb.from_user.id
        )
    except Exception:
        return await cb.answer("Не удалось", show_alert=True)

    await cb.answer("Запрошено обновление" if success else "Не удалось")


@router.callback_query(F.data.startswith("offers:"))
async def cb_show_offers(cb: CallbackQuery, container):
    try:
        product_id = parse_callback_product_id(cb.data)
    except ValueError:
        return await cb.answer("Ошибка в данных товара", show_alert=True)

    try:
        items = await container.api_client.get_offers(
            product_id, limit=DEFAULT_OFFERS_LIMIT
        )
    except Exception:
        return await cb.answer("Не удалось", show_alert=True)

    if not items:
        return await cb.answer("Предложения не найдены", show_alert=True)

    lines = [
        f"{i}. {offer['price']} {offer['currency']} — {offer['shop']['name']}"
        for i, offer in enumerate(items, 1)
    ]

    if cb.message:
        await cb.message.answer("Лучшие предложения:\n" + "\n".join(lines))
    await cb.answer()


@router.callback_query(F.data.startswith("fav-add:"))
async def cb_add_to_favorites(cb: CallbackQuery, container):
    """Обработчик добавления товара в избранное"""
    try:
        product_id = parse_callback_product_id(cb.data)
    except ValueError:
        return await cb.answer("Ошибка в данных товара", show_alert=True)

    try:
        success = await container.api_client.add_favorite(
            product_id, telegram_id=cb.from_user.id
        )
    except Exception:
        return await cb.answer("Не удалось", show_alert=True)

    await cb.answer("Добавлено в избранное" if success else "Уже в избранном")


@router.callback_query(F.data.startswith("alert-new:"))
async def cb_create_alert(cb: CallbackQuery):
    """Обработчик создания алерта - переводит в режим ввода цены"""
    try:
        product_id, currency = parse_alert_new_data(cb.data)
    except ValueError:
        return await cb.answer("Ошибка в данных алерта", show_alert=True)

    set_wait_mode(cb.from_user.id, f"alertNew:{product_id}:{currency}")

    if cb.message:
        await cb.message.answer(
            f"Введите пороговую цену для алерта в {currency} (например 1990.00)"
        )
    await cb.answer()
