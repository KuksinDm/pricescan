import asyncio
import logging

from aiogram import Bot, Dispatcher

from .api import ApiClient
from .handlers.menu import build_router as menu_router
from .handlers.start import build_router as start_router
from .settings import Settings

logger = logging.getLogger("pricescan_bot")
logging.basicConfig(level=logging.INFO)


async def run_async():
    settings = Settings.from_env()
    bot = Bot(settings.bot_token)
    dp = Dispatcher()

    api = ApiClient(
        base_url=settings.api_base_url, service_token=settings.service_token
    )

    dp.include_router(start_router(api))
    dp.include_router(menu_router(api))

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await api.close()


def run():
    asyncio.run(run_async())
