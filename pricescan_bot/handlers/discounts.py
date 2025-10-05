import logging

from aiogram import F, Router
from aiogram.types import Message

from ..constants import DEFAULT_LIMIT
from ..utils.auth import ensure_jwt
from ..utils.keyboards import offer_actions_kb
from ..utils.texts import DISCOUNTS_BTN

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == DISCOUNTS_BTN)
async def btn_discounts(message: Message, container):
    """Обработчик кнопки 'Акции' - показывает товары со скидками"""
    try:
        await ensure_jwt(message, container.api_client)
    except Exception:
        logger.exception("Failed to ensure JWT for discounts")
        return await message.answer("Ошибка авторизации. Попробуйте позже.")

    try:
        # Получаем товары со скидками
        offers = await container.api_client.get_discounts(limit=DEFAULT_LIMIT)
    except Exception:
        logger.exception("Failed to get discounts")
        return await message.answer("Не удалось получить акции.")

    if not offers:
        return await message.answer("Акций пока нет. Проверьте позже!")

    await message.answer("🔥 Товары со скидками:")

    # Отправляем отдельное сообщение для каждого товара
    for offer in offers:
        # Форматируем сообщение с информацией о скидке
        text = format_discount_offer_text(offer)

        # Создаем кнопки для товара
        keyboard = offer_actions_kb(offer["product"], offer["url"], offer["currency"])

        await message.answer(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


def format_discount_offer_text(offer: dict) -> str:
    """Форматирует текст товара со скидкой"""
    # Обрабатываем множественные издатели и категории
    publishers = offer.get("product_publishers", [])
    categories = offer.get("product_categories", [])

    publishers_str = ", ".join(publishers) if publishers else "Неизвестно"
    categories_str = ", ".join(categories) if categories else "Неизвестно"

    # Добавляем информацию о скидке
    discount_info = ""
    if offer.get("discount_percentage"):
        discount_info = f"\n🔥 Скидка: {offer['discount_percentage']:.1f}%"

    return (
        f"Игра: {offer['product_title']}\n"
        f"Издатель: {publishers_str}\n"
        f"Категория: {categories_str}\n"
        f"Игроки: {offer.get('min_players') or '?'}–{offer.get('max_players') or '?'} | "
        f"Время: {offer.get('playtime_min') or '?'} мин | Возраст: {offer.get('min_age') or '?'}+\n"
        f"Цена: {offer['price']} {offer['currency']} | Магазин: {offer['shop']['name']}"
        f"{discount_info}"
    )
