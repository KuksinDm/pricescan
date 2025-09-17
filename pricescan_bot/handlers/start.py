from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..api import ApiClient
from ..utils.auth import ensure_jwt
from ..utils.keyboards import main_menu_kb
from ..utils.texts import HELP_TEXT, WELCOME_TEXT


def build_router(api: ApiClient) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def cmd_start(message: Message):
        await ensure_jwt(message, api)
        await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        await message.answer(HELP_TEXT, reply_markup=main_menu_kb())

    return router
