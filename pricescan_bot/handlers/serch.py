from aiogram import F, Router
from aiogram.types import Message
from ..api import ApiClient
from ..utils.auth import ensure_jwt
from ..services.formatting import format_offer_text
from ..keyboards.common import offer_actions_kb
from ..utils.texts import SEARCH_BTN

router = Router()

@router.message(F.text.startswith(SEARCH_BTN))
async def ask_query(message: Message):
    await message.answer("Введите название игры и отправьте сообщение.")

@router.message(F.text & ~F.text.startswith("/"))
async def do_search(message: Message, api: ApiClient):
    q = (message.text or "").strip()
    if not q:
        return await message.answer("Пустой запрос. Введите название игры.")
    await ensure_jwt(message, api)
    offer = await api.get_cheapest(q)
    if not offer:
        return await message.answer("Ничего не нашлось")
    await message.answer(
        format_offer_text(offer),
        reply_markup=offer_actions_kb(offer["product"], offer["url"], offer["currency"]),
        disable_web_page_preview=True,
    )