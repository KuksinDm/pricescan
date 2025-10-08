import logging

from aiogram import F, Router
from aiogram.types import Message

from ..utils.keyboards import main_menu_kb
from ..utils.texts import HELP_BTN, HELP_TEXT

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.in_([HELP_BTN, "Помощь"]))
async def btn_help(message: Message):
    logger.info(f"User {message.from_user.id} requested help")
    await message.answer(HELP_TEXT, reply_markup=main_menu_kb())
