"""Сервис для обновления страниц после изменений"""

import logging
from typing import TYPE_CHECKING

from ..constants import DEFAULT_PAGE_LIMIT, OFFSET
from ..keyboards.alerts import alerts_kb
from ..keyboards.favorites import favorites_kb

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message

    from ..api import ApiClient

logger = logging.getLogger(__name__)


async def refresh_alerts_page(
    message: "Message", user_id: int, api: "ApiClient", success_msg: str
):
    """Обновляет страницу алертов после изменений"""
    try:
        items, prev_off, next_off = await api.list_alerts_page(
            telegram_id=user_id, limit=DEFAULT_PAGE_LIMIT, offset=OFFSET
        )
        await message.answer(
            success_msg,
            reply_markup=alerts_kb(items, set(), prev_off, next_off) if items else None,
        )
    except Exception:
        logger.exception("Failed to refresh alerts page")
        await message.answer(success_msg)


async def refresh_favorites_page(
    cb: "CallbackQuery", user_id: int, api: "ApiClient", success_msg: str
):
    """Обновляет страницу избранного после изменений"""
    try:
        items, prev_off, next_off = await api.list_favorites_page(
            telegram_id=user_id, limit=DEFAULT_PAGE_LIMIT, offset=OFFSET
        )
        if cb.message:
            if not items:
                await cb.message.edit_reply_markup(reply_markup=None)
                await cb.message.answer("Избранное пусто.")
            else:
                await cb.message.edit_reply_markup(
                    reply_markup=favorites_kb(items, set(), prev_off, next_off)
                )
    except Exception:
        logger.exception("Failed to refresh favorites page")

    await cb.answer(success_msg)
