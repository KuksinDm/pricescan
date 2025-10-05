import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..constants import DEFAULT_PAGE_LIMIT, LARGE_LIMIT, OFFSET
from ..keyboards.alerts import alerts_kb
from ..services.alert_handlers import handle_alert_edit, handle_alert_new
from ..services.page_refresh import refresh_alerts_page
from ..services.state import (
    clear_multi,
    get_selected_ids,
    get_wait_mode,
    set_wait_mode,
    toggle_multi_selected,
)
from ..utils.auth import ensure_jwt
from ..utils.parsers import (
    parse_callback_alert_id,
    parse_callback_offset,
)
from ..utils.texts import ALERTS_BTN

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == ALERTS_BTN)
async def btn_alerts(message: Message, container):
    """Обработчик кнопки 'Подписки' - показывает первую страницу алертов"""
    try:
        await ensure_jwt(message, container.api_client)
    except Exception:
        logger.exception("Failed to ensure JWT for alerts")
        return await message.answer("Ошибка авторизации. Попробуйте позже.")

    try:
        items, prev_off, next_off = await container.api_client.list_alerts_page(
            telegram_id=message.from_user.id, limit=DEFAULT_PAGE_LIMIT, offset=OFFSET
        )
    except Exception:
        logger.exception("Failed to get alerts page")
        return await message.answer("Не удалось получить подписки.")

    if not items:
        return await message.answer("Подписок нет.")

    await message.answer(
        "Подписки:", reply_markup=alerts_kb(items, set(), prev_off, next_off)
    )


@router.callback_query(F.data.startswith("alert-page:"))
async def cb_alerts_page(cb: CallbackQuery, container):
    """Обработчик пагинации алертов - переключает страницы"""
    offset = parse_callback_offset(cb.data)

    try:
        items, prev_off, next_off = await container.api_client.list_alerts_page(
            telegram_id=cb.from_user.id, limit=DEFAULT_PAGE_LIMIT, offset=offset
        )
    except Exception:
        logger.exception("Failed to get alerts page: offset=%s", offset)
        return await cb.answer("Не удалось загрузить страницу", show_alert=True)

    if not items:
        return await cb.answer("Больше нет", show_alert=True)

    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=alerts_kb(items, set(), prev_off, next_off)
        )
    await cb.answer()


@router.callback_query(F.data.startswith("alert-sel:"))
async def cb_alert_select(cb: CallbackQuery, container):
    """Обработчик выбора алерта - добавляет/убирает из множественного выбора"""
    try:
        alert_id = parse_callback_alert_id(cb.data)
    except ValueError:
        return await cb.answer("Ошибка в данных", show_alert=True)

    try:
        items = await container.api_client.list_alerts(
            telegram_id=cb.from_user.id, limit=LARGE_LIMIT
        )
    except Exception:
        logger.exception("Failed to get alerts list for selection")
        return await cb.answer("Не удалось загрузить список", show_alert=True)

    selected = toggle_multi_selected(cb.from_user.id, alert_id)

    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=alerts_kb(items, selected, None, None)
        )
    await cb.answer()


@router.callback_query(F.data == "alert-on-selected")
async def cb_alerts_activate_selected(cb: CallbackQuery, container):
    """Включает все выбранные алерты"""
    user_id = cb.from_user.id
    selected_ids = get_selected_ids(user_id)

    if not selected_ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)

    activated_count = 0
    for alert_id in selected_ids:
        try:
            if await container.api_client.toggle_alert(alert_id, telegram_id=user_id):
                activated_count += 1
        except Exception:
            logger.exception("Failed to activate alert: id=%s", alert_id)

    clear_multi(user_id)
    await refresh_alerts_page(
        cb.message, user_id, container.api_client, f"Включено: {activated_count}"
    )


@router.callback_query(F.data == "alert-off-selected")
async def cb_alerts_deactivate_selected(cb: CallbackQuery, container):
    """Выключает все выбранные алерты"""
    user_id = cb.from_user.id
    selected_ids = get_selected_ids(user_id)

    if not selected_ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)

    deactivated_count = 0
    for alert_id in selected_ids:
        try:
            if await container.api_client.toggle_alert(alert_id, telegram_id=user_id):
                deactivated_count += 1
        except Exception:
            logger.exception("Failed to deactivate alert: id=%s", alert_id)

    clear_multi(user_id)
    await refresh_alerts_page(
        cb.message, user_id, container.api_client, f"Выключено: {deactivated_count}"
    )


@router.callback_query(F.data == "alert-del-selected")
async def cb_alerts_delete_selected(cb: CallbackQuery, container):
    """Удаляет все выбранные алерты"""
    user_id = cb.from_user.id
    selected_ids = get_selected_ids(user_id)

    if not selected_ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)

    deleted_count = 0
    for alert_id in selected_ids:
        try:
            if await container.api_client.delete_alert(alert_id, telegram_id=user_id):
                deleted_count += 1
        except Exception:
            logger.exception("Failed to delete alert: id=%s", alert_id)

    clear_multi(user_id)
    await refresh_alerts_page(
        cb.message, user_id, container.api_client, f"Удалено: {deleted_count}"
    )


@router.callback_query(F.data == "alert-edit-selected")
async def cb_alerts_edit_selected(cb: CallbackQuery):
    """Переводит в режим редактирования цены выбранных алертов"""
    user_id = cb.from_user.id
    selected_ids = get_selected_ids(user_id)

    if not selected_ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)

    if cb.message:
        await cb.message.answer("Введите новую пороговую цену (например 1990.00)")
    # Объединяем ID алертов в строку для режима ожидания
    alert_ids_str = ",".join(map(str, selected_ids))
    set_wait_mode(user_id, f"alertEdit:{alert_ids_str}")

    clear_multi(user_id)
    await cb.answer()


@router.message(F.text.regexp(r"^\d+[\.,]?\d*$"))
async def on_price_input(message: Message, container):
    """Обрабатывает ввод цены для создания/редактирования алертов"""
    user_id = message.from_user.id
    wait_mode = get_wait_mode(user_id)

    if not wait_mode:
        return

    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        return await message.answer("Некорректная цена. Пример: 1990.00")

    if wait_mode.startswith("alertEdit:"):
        await handle_alert_edit(
            message, container.api_client, user_id, price, wait_mode
        )
    elif wait_mode.startswith("alertNew:"):
        await handle_alert_new(message, container.api_client, user_id, price, wait_mode)
