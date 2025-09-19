import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..api import ApiClient
from ..keyboards.favorites import favorites_kb
from ..services.state import clear_multi, get_selected_ids, toggle_multi_selected
from ..utils.auth import ensure_jwt
from ..utils.texts import FAV_BTN

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.startswith(FAV_BTN))
async def btn_fav(message: Message, api: ApiClient):
    u = message.from_user
    await ensure_jwt(message, api)
    try:
        items, prev_off, next_off = await api.list_favorites_page(
            telegram_id=u.id, limit=5, offset=0
        )
    except Exception:
        logger.exception("list_favorites_page failed")
        return await message.answer("Не удалось получить избранное.")
    if not items:
        return await message.answer("Избранное пусто.")
    await message.answer(
        "Избранное:", reply_markup=favorites_kb(items, set(), prev_off, next_off)
    )


@router.callback_query(F.data.startswith("fav-page:"))
async def cb_fav_page(cb: CallbackQuery, api: ApiClient):
    off = int(cb.data.split(":")[1])
    u = cb.from_user
    try:
        items, prev_off, next_off = await api.list_favorites_page(
            telegram_id=u.id, limit=5, offset=off
        )
    except Exception:
        logger.exception("list_favorites_page failed: offset=%s", off)
        return await cb.answer("Не удалось загрузить страницу", show_alert=True)
    if not items:
        return await cb.answer("Больше нет", show_alert=True)
    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=favorites_kb(items, set(), prev_off, next_off)
        )
    await cb.answer()


@router.callback_query(F.data.startswith("fav-sel:"))
async def cb_fav_sel(cb: CallbackQuery, api: ApiClient):
    fid = int(cb.data.split(":")[1])
    u = cb.from_user
    try:
        items = await api.list_favorites(telegram_id=u.id, limit=20)
    except Exception:
        logger.exception("list_favorites failed")
        return await cb.answer("Не удалось загрузить список", show_alert=True)
    selected = toggle_multi_selected(u.id, fid)
    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=favorites_kb(items, selected, None, None)
        )
    await cb.answer()


@router.callback_query(F.data == "fav-del-selected")
async def cb_fav_del_selected(cb: CallbackQuery, api: ApiClient):
    u = cb.from_user
    ids = get_selected_ids(u.id)
    if not ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)
    ok = 0
    for fid in ids:
        try:
            if await api.delete_favorite(fid, telegram_id=u.id):
                ok += 1
        except Exception:
            logger.exception("delete_favorite failed: fav_id=%s", fid)
    clear_multi(u.id)
    try:
        items, prev_off, next_off = await api.list_favorites_page(
            telegram_id=u.id, limit=5, offset=0
        )
    except Exception:
        logger.exception("list_favorites_page failed after delete")
        return await cb.answer(f"Удалено: {ok}")
    if cb.message:
        if not items:
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.answer("Избранное пусто.")
        else:
            await cb.message.edit_reply_markup(
                reply_markup=favorites_kb(items, set(), prev_off, next_off)
            )
    await cb.answer(f"Удалено: {ok}")
