import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..api import ApiClient
from ..services.formatting import format_offer_text_no_description
from ..services.state import set_wait_mode
from ..utils.auth import ensure_jwt
from ..utils.keyboards import offer_actions_kb
from ..utils.texts import SEARCH_BTN, is_button_text

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == SEARCH_BTN)
async def ask_query(message: Message):
    await message.answer("Введите название игры и отправьте сообщение.")


@router.message(
    F.text
    & ~F.text.startswith("/")
    & ~F.text.startswith("fav-")
    & ~F.text.startswith("alert-")
    & ~F.text.func(is_button_text)
    & ~F.text.regexp(r"^\d+[\.,]?\d*$")
)
# async def do_search(message: Message, api: ApiClient):
#     q = (message.text or "").strip()
#     if not q:
#         return await message.answer("Пустой запрос. Введите название игры.")
#     await ensure_jwt(message, api)
#     try:
#         offer = await api.get_cheapest(q)
#     except Exception:
#         logger.exception("get_cheapest failed for query=%r", q)
#         return await message.answer("Сервис временно недоступен. Попробуйте позже.")
#     if not offer:
#         return await message.answer("Ничего не нашлось")
#     # попутно добавим запись в историю (best-effort)
#     try:
#         await api.add_search_history(
#             telegram_id=message.from_user.id, query=q, results_count=1
#         )
#     except Exception:
#         logger.exception("add_search_history failed")
#     try:
#         await message.answer(
#             format_offer_text(offer),
#             reply_markup=offer_actions_kb(
#                 offer["product"], offer["url"], offer["currency"]
#             ),
#             disable_web_page_preview=True,
#         )
#     except Exception:
#         logger.exception("Failed to send offer message")
#         await message.answer("Не удалось отправить сообщение.")
async def do_search(message: Message, api: ApiClient):
    q = (message.text or "").strip()
    if not q:
        return await message.answer("Пустой запрос. Введите название игры.")
    await ensure_jwt(message, api)
    try:
        # Получаем все варианты
        offers = await api.get_cheapest(q)
    except Exception:
        logger.exception("get_cheapest failed for query=%r", q)
        return await message.answer("Сервис временно недоступен. Попробуйте позже.")

    if not offers:
        return await message.answer("Ничего не нашлось")

    # Отправляем отдельное сообщение для каждого товара
    for offer in offers[:5]:  # Максимум 5 товаров
        # Форматируем сообщение без описания
        text = format_offer_text_no_description(offer)
        
        # Создаем кнопки для товара
        keyboard = offer_actions_kb(
            offer["product"], offer["url"], offer["currency"]
        )
        
        await message.answer(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

    # Добавляем в историю поиска
    try:
        await api.add_search_history(
            telegram_id=message.from_user.id, query=q, results_count=len(offers)
        )
    except Exception:
        logger.exception("add_search_history failed")


@router.callback_query(F.data.startswith("refresh:"))
async def cb_refresh(cb: CallbackQuery, api: ApiClient):
    pid = int(cb.data.split(":")[1])
    try:
        ok = await api.refresh_product(pid, telegram_id=cb.from_user.id)
    except Exception:
        logger.exception("refresh_product failed: pid=%s", pid)
        return await cb.answer("Не удалось", show_alert=True)
    await cb.answer("Запрошено обновление" if ok else "Не удалось")


@router.callback_query(F.data.startswith("offers:"))
async def cb_offers(cb: CallbackQuery, api: ApiClient):
    pid = int(cb.data.split(":")[1])
    try:
        items = await api.get_offers(pid, limit=5)
    except Exception:
        logger.exception("get_offers failed: pid=%s", pid)
        return await cb.answer("Не удалось", show_alert=True)
    if not items:
        return await cb.answer("Предложения не найдены", show_alert=True)
    lines = [
        f"{i}. {o['price']} {o['currency']} — {o['shop']['name']}"
        for i, o in enumerate(items, 1)
    ]
    if cb.message:
        await cb.message.answer("Лучшие предложения:\n" + "\n".join(lines))
    await cb.answer()


@router.callback_query(F.data.startswith("fav-add:"))
async def cb_fav_add(cb: CallbackQuery, api: ApiClient):
    pid = int(cb.data.split(":")[1])
    try:
        ok = await api.add_favorite(pid, telegram_id=cb.from_user.id)
    except Exception:
        logger.exception("add_favorite failed: pid=%s", pid)
        return await cb.answer("Не удалось", show_alert=True)
    await cb.answer("Добавлено в избранное" if ok else "Уже в избранном")


@router.callback_query(F.data.startswith("alert-new:"))
async def cb_alert_new(cb: CallbackQuery):
    # format: alert-new:{product_id}:{currency}
    parts = cb.data.split(":")
    pid = int(parts[1])
    currency = parts[2] if len(parts) > 2 else "RUB"

    set_wait_mode(cb.from_user.id, f"alertNew:{pid}:{currency}")
    if cb.message:
        await cb.message.answer(
            f"Введите пороговую цену для алерта в {currency} (например 1990.00)"
        )
    await cb.answer()
