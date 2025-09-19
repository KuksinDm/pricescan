import logging

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from ..api import ApiClient
from ..services.formatting import fmt_dt_iso
from ..utils.auth import ensure_jwt
from ..utils.texts import HISTORY_BTN

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.startswith(HISTORY_BTN))
async def show_history(message: Message, api: ApiClient):
    u = message.from_user
    await ensure_jwt(message, api)
    try:
        items = await api.get_search_history(telegram_id=u.id, limit=10)
    except Exception:
        logger.exception("get_search_history failed")
        return await message.answer("Не удалось получить историю.")
    if not items:
        return await message.answer("История пуста.")
    lines = [
        f"{i}. «{it['query']}» — {fmt_dt_iso(it.get('search_date'))}"
        for i, it in enumerate(items, 1)
    ]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Очистить историю", callback_data="hist-clear")]
        ]
    )
    await message.answer("Последние запросы:\n\n" + "\n".join(lines), reply_markup=kb)


@router.callback_query(F.data == "hist-clear")
async def cb_hist_clear(cb: CallbackQuery, api: ApiClient):
    try:
        ok = await api.clear_search_history(telegram_id=cb.from_user.id)
    except Exception:
        logger.exception("clear_search_history failed")
        return await cb.answer("Не удалось очистить", show_alert=True)
    if cb.message:
        if ok:
            await cb.message.edit_text("История очищена.")
        else:
            await cb.message.edit_text("Не удалось очистить историю.")
    await cb.answer()
