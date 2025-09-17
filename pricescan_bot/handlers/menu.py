from typing import Iterable

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from ..api import ApiClient
from ..utils.auth import ensure_jwt
from ..utils.keyboards import offer_actions_kb
from ..utils.state import (
    clear_multi,
    clear_wait_mode,
    get_selected_ids,
    get_wait_mode,
    set_multi_mode,
    set_wait_mode,
    toggle_multi_selected,
)
from ..utils.texts import (
    ALERTS_BTN,
    FAV_BTN,
    HELP_BTN,
    HELP_TEXT,
    HISTORY_BTN,
    SEARCH_BTN,
    is_button_text,
)


def _basic_router() -> Router:
    r = Router()

    @r.message(F.text.in_([HELP_BTN, "Помощь"]))
    async def btn_help(message: Message):
        await message.answer(HELP_TEXT)

    return r


def _build_multi_kb(
    items: Iterable[dict],
    selected: set[int],
    ctx: str,
    prev_off: int | None = None,
    next_off: int | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for it in items:
        mark = "✅ " if it.get("id") in selected else ""
        base_title = it.get("product_title") or str(it.get("product"))
        if ctx == "alert":
            status = "вкл" if it.get("is_active") else "выкл"
            thr = it.get("threshold_price")
            cur = it.get("currency") or ""
            thr_part = f" ≤ {thr} {cur}" if thr is not None else ""
            label = f"{mark}{base_title}{thr_part} — {status}"
        else:
            label = f"{mark}{base_title}"

        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"{ctx}-sel:{it['id']}")
        ])

        if ctx == "fav":
            pid = it.get("product")
            if pid is not None:
                url = it.get("first_offer_url")
                rows.append([
                    InlineKeyboardButton(
                        text="Обновить", callback_data=f"refresh:{pid}"
                    ),
                    InlineKeyboardButton(
                        text="Открыть",
                        url=url if url else None,
                        callback_data=(None if url else f"fav-open:{pid}"),
                    ),
                ])

    if ctx == "fav":
        rows += [
            [
                InlineKeyboardButton(
                    text="Удалить выбранные", callback_data="fav-del-selected"
                )
            ]
        ]
    else:
        rows += [
            [
                InlineKeyboardButton(
                    text="Включить выбранные", callback_data="alert-on-selected"
                ),
                InlineKeyboardButton(
                    text="Выключить выбранные", callback_data="alert-off-selected"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Удалить выбранные", callback_data="alert-del-selected"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Изменить цену выбранных", callback_data="alert-edit-selected"
                )
            ],
        ]

    nav: list[InlineKeyboardButton] = []
    if prev_off is not None:
        nav.append(
            InlineKeyboardButton(text="◀︎", callback_data=f"{ctx}-page:{prev_off}")
        )
    if next_off is not None:
        nav.append(
            InlineKeyboardButton(text="▶︎", callback_data=f"{ctx}-page:{next_off}")
        )
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _actions_router(api: ApiClient) -> Router:
    r = Router()

    @r.message(F.text.startswith(SEARCH_BTN))
    async def btn_find(message: Message):
        if not message.from_user:
            return
        set_wait_mode(message.from_user.id, "find")
        await message.answer("Введите название игры и отправьте сообщение.")

    # общий обработчик ввода — действует только в режиме 'find'
    @r.message(F.text & ~F.text.startswith("/") & ~F.text.func(is_button_text))
    async def handle_by_mode(message: Message):
        u = message.from_user
        mode = get_wait_mode(u.id) if u else None
        if not u or not mode:
            return
            # Режим создания алерта: 'alert:<product_id>:<currency>'

        if mode.startswith("alert:"):
            parts = mode.split(":")
            try:
                pid = int(parts[1])
                currency = parts[2] if len(parts) > 2 else "RUB"
                value = float((message.text or "").replace(",", "."))
            except Exception:
                await message.answer("Введите цену числом, например 1990")
                return
            clear_wait_mode(u.id)
            await ensure_jwt(message, api)
            ok = await api.create_alert(
                telegram_id=u.id,
                product_id=pid,
                threshold_price=value,
                currency=currency,
            )
            await message.answer(
                "Подписка создана" if ok else "Не удалось создать подписку"
            )
            return

        if mode.startswith("alertEdit:"):
            try:
                value = float((message.text or "").replace(",", "."))
            except Exception:
                await message.answer("Введите цену числом, например 1990")
                return
            ids_str = mode.split(":", 1)[1]
            ids = [int(x) for x in ids_str.split(",") if x.strip().isdigit()]
            clear_wait_mode(u.id)
            updated = 0
            for aid in ids:
                if await api.update_alert_price(
                    aid, telegram_id=u.id, threshold_price=value
                ):
                    updated += 1
            # после обновления перечитать и перерисовать список
            items = await api.list_alerts(telegram_id=u.id, limit=20)
            if not items:
                await message.answer("Подписок нет.")
            else:
                await message.answer("Готово. Обновлено: %d" % updated)
            return

        clear_wait_mode(u.id)
        await ensure_jwt(message, api)
        # Старый режим поиска
        if mode != "find":
            return
        q = (message.text or "").strip()
        if not q:
            await message.answer("Пустой запрос. Введите название игры.")
            return
        offer = await api.get_cheapest(q)
        if not offer:
            await message.answer("Ничего не нашлось")
            return

        # сохранить запрос в истории (не критично, если не удастся)
        try:
            await api.add_search_history(telegram_id=u.id, query=q, results_count=1)
        except Exception:
            pass

        text = (
            f"Игра: {offer['product_title']}\n"
            f"Автор: {offer.get('product_author') or '-'} | Издатель: {offer.get('product_publisher') or '-'}\n"
            f"Категория: {offer.get('product_category') or '-'}\n"
            f"Игроки: {offer.get('min_players') or '?'}–{offer.get('max_players') or '?'} | Время: {offer.get('playtime_min') or '?'} мин | Возраст: {offer.get('min_age') or '?'}+\n"
            f"Цена: {offer['price']} {offer['currency']} | Магазин: {offer['shop']['name']}\n"
            f"\n{(offer.get('description') or '')[:400]}"
        )
        await message.answer(
            text,
            reply_markup=offer_actions_kb(
                offer["product"], offer["url"], offer["currency"]
            ),
            disable_web_page_preview=True,
        )

    # История (кнопка в нижнем меню)
    @r.message(F.text.startswith(HISTORY_BTN))
    async def btn_history(message: Message):
        u = message.from_user
        await ensure_jwt(message, api)
        items = await api.get_search_history(telegram_id=u.id, limit=10)
        if not items:
            await message.answer("История пуста.")
            return

        def fmt(ts: str) -> str:
            ts = (ts or "").replace("Z", "+00:00")
            return ts.replace("T", " ")[:16]  # YYYY-MM-DD HH:MM

        lines = [
            f"{i}. «{it['query']}» — {fmt(it.get('search_date'))}"
            for i, it in enumerate(items, 1)
        ]
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Очистить историю", callback_data="hist-clear"
                    )
                ]
            ]
        )
        await message.answer(
            "Последние запросы:\n\n" + "\n".join(lines), reply_markup=kb
        )

    # Избранное (реальная логика в actions-роутере)

    @r.message(F.text.startswith(FAV_BTN))
    async def btn_fav(message: Message):
        u = message.from_user
        await ensure_jwt(message, api)
        items, prev_off, next_off = await api.list_favorites_page(
            telegram_id=u.id, limit=5, offset=0
        )
        if not items:
            await message.answer("Избранное пусто.")
            return
        set_multi_mode(u.id, "fav")
        kb = _build_multi_kb(items, set(), "fav", prev_off, next_off)
        await message.answer("Избранное:", reply_markup=kb)

    @r.message(F.text.startswith(ALERTS_BTN))
    async def btn_alerts(message: Message):
        u = message.from_user
        await ensure_jwt(message, api)
        items, prev_off, next_off = await api.list_alerts_page(
            telegram_id=u.id, limit=5, offset=0
        )
        if not items:
            await message.answer("Подписок нет.")
            return
        set_multi_mode(u.id, "alert")
        kb = _build_multi_kb(items, set(), "alert", prev_off, next_off)
        await message.answer("Ваши подписки:", reply_markup=kb)

    return r


def _callbacks_router(api: ApiClient) -> Router:
    r = Router()

    @r.callback_query(F.data.startswith("refresh:"))
    async def cb_refresh(cb: CallbackQuery):
        try:
            pid = int(cb.data.split(":", 1)[1])
        except Exception:
            await cb.answer("Некорректный ID", show_alert=True)
            return
        u = cb.from_user
        await api.ensure_jwt(
            telegram_id=u.id,
            telegram_username=u.username,
            first_name=u.first_name,
            last_name=u.last_name,
            language_code=getattr(u, "language_code", None),
        )
        ok = await api.refresh_product(pid, telegram_id=u.id)
        await cb.answer("Запрос отправлен" if ok else "Не удалось", show_alert=not ok)

    @r.callback_query(F.data.startswith("offers:"))
    async def cb_offers(cb: CallbackQuery):
        parts = cb.data.split(":", 2)  # offers:<id>[:limit]
        try:
            pid = int(parts[1])
            limit = int(parts[2]) if len(parts) > 2 else 5
        except Exception:
            await cb.answer("Некорректный запрос", show_alert=True)
            return
        items = await api.get_offers(pid, limit=limit)
        if not items:
            await cb.answer("Предложения не найдены", show_alert=True)
            return
        lines = [
            f"{i}. {o['shop']['name']}: {o['price']} {o['currency']}\n{o['url']}"
            for i, o in enumerate(items, 1)
        ]
        if cb.message:
            await cb.message.answer(
                "Топ предложений:\n\n" + "\n\n".join(lines),
                disable_web_page_preview=True,
            )
        await cb.answer()

    # открыть первую ссылку из офферов (shortcut из избранного)

    @r.callback_query(F.data.startswith("fav-open:"))
    async def cb_fav_open(cb: CallbackQuery):
        try:
            pid = int(cb.data.split(":", 1)[1])
        except Exception:
            await cb.answer("Некорректный ID", show_alert=True)
            return
        items = await api.get_offers(pid, limit=1)
        if not items:
            await cb.answer("Нет ссылок", show_alert=True)
            return
        url = items[0].get("url")
        if cb.message and url:
            await cb.message.answer(url, disable_web_page_preview=True)
        await cb.answer()

    @r.callback_query(F.data == "hist-clear")
    async def cb_hist_clear(cb: CallbackQuery):
        u = cb.from_user
        ok = await api.clear_search_history(telegram_id=u.id)
        await cb.answer("История очищена" if ok else "Не удалось", show_alert=not ok)

    @r.callback_query(F.data.startswith("fav-add:"))
    async def cb_fav_add(cb: CallbackQuery):
        pid = int(cb.data.split(":")[1])
        u = cb.from_user
        await api.ensure_jwt(
            telegram_id=u.id,
            telegram_username=u.username,
            first_name=u.first_name,
            last_name=u.last_name,
            language_code=getattr(u, "language_code", None),
        )
        ok = await api.add_favorite(pid, telegram_id=u.id)
        await cb.answer(
            "Добавлено в избранное" if ok else "Не удалось", show_alert=not ok
        )

    @r.callback_query(F.data.startswith("fav-sel:"))
    async def cb_fav_sel(cb: CallbackQuery):
        fid = int(cb.data.split(":")[1])
        u = cb.from_user
        if not cb.message:
            await cb.answer()
            return
        # перечитаем список для актуальной разметки
        items = await api.list_favorites(telegram_id=u.id, limit=20)
        selected = toggle_multi_selected(u.id, fid)
        # перестроить клавиатуру
        kb = _build_multi_kb(items, selected, "fav")
        await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer()

    @r.callback_query(F.data == "fav-del-selected")
    async def cb_fav_del_selected(cb: CallbackQuery):
        u = cb.from_user
        ids = get_selected_ids(u.id)
        if not ids:
            await cb.answer("Ничего не выбрано", show_alert=True)
            return
        ok_cnt = 0
        for fid in ids:
            if await api.delete_favorite(fid, telegram_id=u.id):
                ok_cnt += 1
        clear_multi(u.id)
        # обновим список избранного сразу
        items = await api.list_favorites(telegram_id=u.id, limit=20)
        if cb.message:
            if not items:
                await cb.message.edit_reply_markup(reply_markup=None)
                await cb.message.answer("Избранное пусто.")
            else:
                kb = _build_multi_kb(items, set(), "fav")
                await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer(f"Удалено: {ok_cnt}")

    @r.callback_query(F.data == "fav-cancel")
    async def cb_fav_cancel(cb: CallbackQuery):
        clear_multi(cb.from_user.id)
        await cb.answer()
        if cb.message:
            await cb.message.edit_reply_markup(reply_markup=None)

    @r.callback_query(F.data.startswith("alert-new:"))
    async def cb_alert_new(cb: CallbackQuery):
        parts = cb.data.split(":")
        pid = int(parts[1])
        currency = parts[2] if len(parts) > 2 else "RUB"
        set_wait_mode(cb.from_user.id, f"alert:{pid}:{currency}")
        await cb.answer()
        if cb.message:
            await cb.message.answer("Введите пороговую цену (например 1990.00)")

    @r.callback_query(F.data == "alert-edit-selected")
    async def cb_alert_edit_selected(cb: CallbackQuery):
        u = cb.from_user
        ids = get_selected_ids(u.id)
        if not ids:
            await cb.answer("Ничего не выбрано", show_alert=True)
            return
        # Сохраняем режим редактирования с перечнем id
        set_wait_mode(u.id, "alertEdit:" + ",".join(map(str, ids)))
        await cb.answer()
        if cb.message:
            await cb.message.answer("Введите новую цену (например 1990.00)")

    @r.callback_query(F.data.startswith("alert-toggle:"))
    async def cb_alert_toggle(cb: CallbackQuery):
        aid = int(cb.data.split(":")[1])
        u = cb.from_user
        ok = await api.toggle_alert(aid, telegram_id=u.id)
        # обновить список
        items = await api.list_alerts(telegram_id=u.id, limit=20)
        if cb.message:
            if not items:
                await cb.message.edit_reply_markup(reply_markup=None)
                await cb.message.answer("Подписок нет.")
            else:
                kb = _build_multi_kb(items, set(), "alert")
                await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer("Готово" if ok else "Не удалось", show_alert=not ok)

    @r.callback_query(F.data.startswith("alert-del:"))
    async def cb_alert_del(cb: CallbackQuery):
        aid = int(cb.data.split(":")[1])
        u = cb.from_user
        ok = await api.delete_alert(aid, telegram_id=u.id)
        # обновить список
        items = await api.list_alerts(telegram_id=u.id, limit=20)
        if cb.message:
            if not items:
                await cb.message.edit_reply_markup(reply_markup=None)
                await cb.message.answer("Подписок нет.")
            else:
                kb = _build_multi_kb(items, set(), "alert")
                await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer("Удалено" if ok else "Не удалось", show_alert=not ok)

    @r.callback_query(F.data.startswith("alert-sel:"))
    async def cb_alert_sel(cb: CallbackQuery):
        aid = int(cb.data.split(":")[1])
        u = cb.from_user
        if not cb.message:
            await cb.answer()
            return
        items = await api.list_alerts(telegram_id=u.id, limit=20)
        selected = toggle_multi_selected(u.id, aid)
        kb = _build_multi_kb(items, selected, "alert")
        await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer()

    @r.callback_query(F.data == "alert-on-selected")
    async def cb_alert_on_selected(cb: CallbackQuery):
        u = cb.from_user
        ids = get_selected_ids(u.id)
        if not ids:
            await cb.answer("Ничего не выбрано", show_alert=True)
            return
        items = await api.list_alerts(telegram_id=u.id, limit=100)
        id_to_active = {it["id"]: it["is_active"] for it in items}
        changed = 0
        for aid in ids:
            if not id_to_active.get(aid, True):
                if await api.toggle_alert(aid, telegram_id=u.id):
                    changed += 1
        clear_multi(u.id)
        # обновить список
        updated = await api.list_alerts(telegram_id=u.id, limit=20)
        if cb.message:
            if not updated:
                await cb.message.edit_reply_markup(reply_markup=None)
                await cb.message.answer("Подписок нет.")
            else:
                kb = _build_multi_kb(updated, set(), "alert")
                await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer(f"Включено: {changed}")

    @r.callback_query(F.data == "alert-off-selected")
    async def cb_alert_off_selected(cb: CallbackQuery):
        u = cb.from_user
        ids = get_selected_ids(u.id)
        if not ids:
            await cb.answer("Ничего не выбрано", show_alert=True)
            return
        items = await api.list_alerts(telegram_id=u.id, limit=100)
        id_to_active = {it["id"]: it["is_active"] for it in items}
        changed = 0
        for aid in ids:
            if id_to_active.get(aid, False):
                if await api.toggle_alert(aid, telegram_id=u.id):
                    changed += 1
        clear_multi(u.id)
        updated = await api.list_alerts(telegram_id=u.id, limit=20)
        if cb.message:
            if not updated:
                await cb.message.edit_reply_markup(reply_markup=None)
                await cb.message.answer("Подписок нет.")
            else:
                kb = _build_multi_kb(updated, set(), "alert")
                await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer(f"Выключено: {changed}")

    @r.callback_query(F.data == "alert-del-selected")
    async def cb_alert_del_selected(cb: CallbackQuery):
        u = cb.from_user
        ids = get_selected_ids(u.id)
        if not ids:
            await cb.answer("Ничего не выбрано", show_alert=True)
            return
        deleted = 0
        for aid in ids:
            if await api.delete_alert(aid, telegram_id=u.id):
                deleted += 1
        clear_multi(u.id)
        updated = await api.list_alerts(telegram_id=u.id, limit=20)
        if cb.message:
            if not updated:
                await cb.message.edit_reply_markup(reply_markup=None)
                await cb.message.answer("Подписок нет.")
            else:
                kb = _build_multi_kb(updated, set(), "alert")
                await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer(f"Удалено: {deleted}")

    @r.callback_query(F.data == "alert-cancel")
    async def cb_alert_cancel(cb: CallbackQuery):
        clear_multi(cb.from_user.id)
        await cb.answer()
        if cb.message:
            await cb.message.edit_reply_markup(reply_markup=None)

    @r.callback_query(F.data.startswith("fav-page:"))
    async def cb_fav_page(cb: CallbackQuery):
        off = int(cb.data.split(":")[1])
        u = cb.from_user
        items, prev_off, next_off = await api.list_favorites_page(
            telegram_id=u.id, limit=5, offset=off
        )
        if not items:
            await cb.answer("Больше нет", show_alert=True)
            return
        kb = _build_multi_kb(items, set(), "fav", prev_off, next_off)
        if cb.message:
            await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer()

    @r.callback_query(F.data.startswith("alert-page:"))
    async def cb_alert_page(cb: CallbackQuery):
        off = int(cb.data.split(":")[1])
        u = cb.from_user
        items, prev_off, next_off = await api.list_alerts_page(
            telegram_id=u.id, limit=5, offset=off
        )
        if not items:
            await cb.answer("Больше нет", show_alert=True)
            return
        kb = _build_multi_kb(items, set(), "alert", prev_off, next_off)
        if cb.message:
            await cb.message.edit_reply_markup(reply_markup=kb)
        await cb.answer()

    return r


def build_router(api: ApiClient) -> Router:
    root = Router()
    root.include_router(_basic_router())
    root.include_router(_actions_router(api))
    root.include_router(_callbacks_router(api))
    return root
