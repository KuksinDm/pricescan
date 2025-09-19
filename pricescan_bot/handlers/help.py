from aiogram import F, Router
from aiogram.types import Message

from ..utils.keyboards import main_menu_kb
from ..utils.texts import HELP_BTN, HELP_TEXT

router = Router()


@router.message(F.text.in_([HELP_BTN, "Помощь"]))
async def btn_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=main_menu_kb())
