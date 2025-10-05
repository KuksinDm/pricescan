"""Обработчики для алертов"""

import logging
from typing import TYPE_CHECKING

from ..api import ApiClient
from ..services.state import clear_wait_mode
from ..utils.parsers import parse_alert_new_data
from .page_refresh import refresh_alerts_page

if TYPE_CHECKING:
    from aiogram.types import Message


logger = logging.getLogger(__name__)


async def handle_alert_edit(
    message: "Message", api: "ApiClient", user_id: int, price: float, wait_mode: str
):
    """Обрабатывает редактирование цены алерта"""
    try:
        alert_ids = [int(x) for x in wait_mode.split(":", 1)[1].split(",") if x]
    except ValueError:
        logger.error(f"Invalid alert IDs in wait_mode: {wait_mode}")
        return await message.answer("Ошибка в данных подписки")

    updated = 0
    for alert_id in alert_ids:
        try:
            if await api.update_alert_price(
                alert_id, telegram_id=user_id, threshold_price=price
            ):
                updated += 1
        except Exception:
            logger.exception("Failed to update alert price: id=%s", alert_id)

    clear_wait_mode(user_id)
    await refresh_alerts_page(message, user_id, api, f"Обновлено цен: {updated}")


async def handle_alert_new(
    message: "Message", api: "ApiClient", user_id: int, price: float, wait_mode: str
):
    """Обрабатывает создание нового алерта"""
    try:
        product_id, currency = parse_alert_new_data(wait_mode)
    except ValueError:
        return await message.answer("Ошибка в данных товара")

    try:
        success = await api.create_alert(
            telegram_id=user_id,
            product_id=product_id,
            threshold_price=price,
            currency=currency,
        )
    except Exception:
        logger.exception("Failed to create alert: product_id=%s", product_id)
        return await message.answer("Не удалось создать подписку")

    clear_wait_mode(user_id)
    await message.answer(
        "Подписка создана" if success else "Не удалось создать подписку"
    )
