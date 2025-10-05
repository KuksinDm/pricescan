import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..constants import DEFAULT_PAGE_LIMIT, MEDIUM_LIMIT, OFFSET
from ..keyboards.favorites import favorites_kb
from ..services.page_refresh import refresh_favorites_page
from ..services.state import clear_multi, get_selected_ids, toggle_multi_selected
from ..utils.auth import ensure_jwt
from ..utils.parsers import (
    parse_callback_favorite_id,
    parse_callback_offset,
)
from ..utils.texts import FAV_BTN

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.startswith(FAV_BTN))
async def btn_favorites(message: Message, container):
    """Обработчик кнопки 'Избранное' - показывает первую страницу избранного"""
    try:
        await ensure_jwt(message, container.api_client)
    except Exception:
        logger.exception("Failed to ensure JWT for favorites")
        return await message.answer("Ошибка авторизации. Попробуйте позже.")

    try:
        items, prev_off, next_off = await container.api_client.list_favorites_page(
            telegram_id=message.from_user.id, limit=DEFAULT_PAGE_LIMIT, offset=OFFSET
        )
    except Exception:
        logger.exception("Failed to get favorites page")
        return await message.answer("Не удалось получить избранное.")

    if not items:
        return await message.answer("Избранное пусто.")

    await message.answer(
        "Избранное:", reply_markup=favorites_kb(items, set(), prev_off, next_off)
    )


@router.callback_query(F.data.startswith("fav-page:"))
async def cb_favorites_page(cb: CallbackQuery, container):
    """Обработчик пагинации избранного - переключает страницы"""
    offset = parse_callback_offset(cb.data)

    try:
        items, prev_off, next_off = await container.api_client.list_favorites_page(
            telegram_id=cb.from_user.id, limit=DEFAULT_PAGE_LIMIT, offset=offset
        )
    except Exception:
        logger.exception("Failed to get favorites page: offset=%s", offset)
        return await cb.answer("Не удалось загрузить страницу", show_alert=True)

    if not items:
        return await cb.answer("Больше нет", show_alert=True)

    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=favorites_kb(items, set(), prev_off, next_off)
        )
    await cb.answer()


@router.callback_query(F.data.startswith("fav-sel:"))
async def cb_favorite_select(cb: CallbackQuery, container):
    """Обработчик выбора избранного - добавляет/убирает из множественного выбора"""
    try:
        favorite_id = parse_callback_favorite_id(cb.data)
    except ValueError:
        return await cb.answer("Ошибка в данных", show_alert=True)

    try:
        items = await container.api_client.list_favorites(
            telegram_id=cb.from_user.id, limit=MEDIUM_LIMIT
        )
    except Exception:
        logger.exception("Failed to get favorites list for selection")
        return await cb.answer("Не удалось загрузить список", show_alert=True)

    selected = toggle_multi_selected(cb.from_user.id, favorite_id)

    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=favorites_kb(items, selected, None, None)
        )
    await cb.answer()


@router.callback_query(F.data == "fav-del-selected")
async def cb_favorites_delete_selected(cb: CallbackQuery, container):
    """Удаляет все выбранные избранные товары"""
    user_id = cb.from_user.id
    selected_ids = get_selected_ids(user_id)

    if not selected_ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)

    deleted_count = 0
    for favorite_id in selected_ids:
        try:
            if await container.api_client.delete_favorite(
                favorite_id, telegram_id=user_id
            ):
                deleted_count += 1
        except Exception:
            logger.exception("Failed to delete favorite: id=%s", favorite_id)

    clear_multi(user_id)
    await refresh_favorites_page(
        cb, user_id, container.api_client, f"Удалено: {deleted_count}"
    )
