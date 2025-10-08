import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..utils.auth import ensure_jwt
from ..utils.keyboards import main_menu_kb
from ..utils.texts import HELP_TEXT, WELCOME_TEXT

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message, container):
    logger.info(f"User {message.from_user.id} started the bot")

    try:
        await ensure_jwt(message, container.api_client)
        await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())
    except Exception:
        logger.exception("Failed to ensure JWT for start command")
        await message.answer("Ошибка авторизации. Попробуйте позже.")


@router.message(Command("help"))
async def cmd_help(message: Message, container):
    logger.info(f"User {message.from_user.id} requested help via command")

    try:
        await ensure_jwt(message, container.api_client)
        await message.answer(HELP_TEXT, reply_markup=main_menu_kb())
    except Exception:
        logger.exception("Failed to ensure JWT for help command")
        await message.answer("Ошибка авторизации. Попробуйте позже.")
