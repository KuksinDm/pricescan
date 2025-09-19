import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..api import ApiClient
from ..keyboards.alerts import alerts_kb
from ..services.state import (
    clear_multi,
    clear_wait_mode,
    get_selected_ids,
    get_wait_mode,
    set_wait_mode,
    toggle_multi_selected,
)
from ..utils.auth import ensure_jwt
from ..utils.texts import ALERTS_BTN

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.startswith(ALERTS_BTN))
async def btn_alerts(message: Message, api: ApiClient):
    u = message.from_user
    await ensure_jwt(message, api)
    try:
        items, prev_off, next_off = await api.list_alerts_page(
            telegram_id=u.id, limit=5, offset=0
        )
    except Exception:
        logger.exception("list_alerts_page failed")
        return await message.answer("Не удалось получить подписки.")
    if not items:
        return await message.answer("Подписок нет.")
    await message.answer(
        "Ваши подписки:", reply_markup=alerts_kb(items, set(), prev_off, next_off)
    )


@router.callback_query(F.data.startswith("alert-page:"))
async def cb_alert_page(cb: CallbackQuery, api: ApiClient):
    off = int(cb.data.split(":")[1])
    u = cb.from_user
    try:
        items, prev_off, next_off = await api.list_alerts_page(
            telegram_id=u.id, limit=5, offset=off
        )
    except Exception:
        logger.exception("list_alerts_page failed: offset=%s", off)
        return await cb.answer("Не удалось загрузить страницу", show_alert=True)
    if not items:
        return await cb.answer("Больше нет", show_alert=True)
    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=alerts_kb(items, set(), prev_off, next_off)
        )
    await cb.answer()


@router.callback_query(F.data.startswith("alert-sel:"))
async def cb_alert_sel(cb: CallbackQuery, api: ApiClient):
    aid = int(cb.data.split(":")[1])
    u = cb.from_user
    try:
        items = await api.list_alerts(telegram_id=u.id, limit=20)
    except Exception:
        logger.exception("list_alerts failed")
        return await cb.answer("Не удалось загрузить список", show_alert=True)
    selected = toggle_multi_selected(u.id, aid)
    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=alerts_kb(items, selected, None, None)
        )
    await cb.answer()


@router.callback_query(F.data == "alert-on-selected")
async def cb_alert_on_selected(cb: CallbackQuery, api: ApiClient):
    u = cb.from_user
    ids = get_selected_ids(u.id)
    if not ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)
    changed = 0
    items = await api.list_alerts(telegram_id=u.id, limit=100)
    is_active = {it["id"]: it["is_active"] for it in items}
    for aid in ids:
        if not is_active.get(aid, True):
            if await api.toggle_alert(aid, telegram_id=u.id):
                changed += 1
    clear_multi(u.id)
    page, prev_off, next_off = await api.list_alerts_page(
        telegram_id=u.id, limit=5, offset=0
    )
    if cb.message:
        await cb.message.edit_reply_markup(
            reply_markup=alerts_kb(page, set(), prev_off, next_off)
        )
    await cb.answer(f"Включено: {changed}")


@router.callback_query(F.data == "alert-edit-selected")
async def cb_alert_edit_selected(cb: CallbackQuery):
    u = cb.from_user
    ids = get_selected_ids(u.id)
    if not ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)
    set_wait_mode(u.id, "alertEdit:" + ",".join(map(str, ids)))
    if cb.message:
        await cb.message.answer("Введите новую цену (например 1990.00)")
    await cb.answer()


@router.callback_query(F.data == "alert-off-selected")
async def cb_alert_off_selected(cb: CallbackQuery, api: ApiClient):
    u = cb.from_user
    ids = get_selected_ids(u.id)
    if not ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)
    changed = 0
    try:
        items = await api.list_alerts(telegram_id=u.id, limit=100)
    except Exception:
        logger.exception("list_alerts failed")
        return await cb.answer("Не удалось", show_alert=True)
    is_active = {it["id"]: it["is_active"] for it in items}
    for aid in ids:
        if is_active.get(aid, False):
            try:
                if await api.toggle_alert(aid, telegram_id=u.id):
                    changed += 1
            except Exception:
                logger.exception("toggle_alert failed: id=%s", aid)
    clear_multi(u.id)
    page, prev_off, next_off = await api.list_alerts_page(
        telegram_id=u.id, limit=5, offset=0
    )
    if cb.message:
        if not page:
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.answer("Подписок нет.")
        else:
            await cb.message.edit_reply_markup(
                reply_markup=alerts_kb(page, set(), prev_off, next_off)
            )
    await cb.answer(f"Выключено: {changed}")


@router.callback_query(F.data == "alert-del-selected")
async def cb_alert_del_selected(cb: CallbackQuery, api: ApiClient):
    u = cb.from_user
    ids = get_selected_ids(u.id)
    if not ids:
        return await cb.answer("Ничего не выбрано", show_alert=True)
    deleted = 0
    for aid in ids:
        try:
            if await api.delete_alert(aid, telegram_id=u.id):
                deleted += 1
        except Exception:
            logger.exception("delete_alert failed: id=%s", aid)
    clear_multi(u.id)
    page, prev_off, next_off = await api.list_alerts_page(
        telegram_id=u.id, limit=5, offset=0
    )
    if cb.message:
        if not page:
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.answer("Подписок нет.")
        else:
            await cb.message.edit_reply_markup(
                reply_markup=alerts_kb(page, set(), prev_off, next_off)
            )
    await cb.answer(f"Удалено: {deleted}")


@router.message(F.text.regexp(r"^\d+[\.,]?\d*$"))
async def on_price_input(message: Message, api: ApiClient):
    u = message.from_user
    mode = get_wait_mode(u.id)
    if not mode:
        return
    text = (message.text or "").replace(",", ".")
    try:
        price = float(text)
    except ValueError:
        return await message.answer("Некорректная цена. Пример: 1990.00")
    if mode.startswith("alertEdit:"):
        ids = [int(x) for x in mode.split(":", 1)[1].split(",") if x]
        ok = 0
        for aid in ids:
            try:
                if await api.update_alert_price(
                    aid, telegram_id=u.id, threshold_price=price
                ):
                    ok += 1
            except Exception:
                logger.exception("update_alert_price failed: id=%s", aid)
        clear_wait_mode(u.id)
        # обновим список
        items, prev_off, next_off = await api.list_alerts_page(
            telegram_id=u.id, limit=5, offset=0
        )
        await message.answer(
            f"Обновлено цен: {ok}",
            reply_markup=alerts_kb(items, set(), prev_off, next_off) if items else None,
        )
        return
    if mode.startswith("alertNew:"):
        # alertNew:{pid}:{currency}
        _, pid, currency = mode.split(":", 2)
        try:
            ok = await api.create_alert(
                telegram_id=u.id,
                product_id=int(pid),
                threshold_price=price,
                currency=currency,
            )
        except Exception:
            logger.exception("create_alert failed: pid=%s", pid)
            return await message.answer("Не удалось создать подписку")
        clear_wait_mode(u.id)
        await message.answer(
            "Подписка создана" if ok else "Не удалось создать подписку"
        )
