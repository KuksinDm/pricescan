# pricescan_bot/app.py
import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties

from .api import ApiClient
from .handlers import alerts, favorites, help, history, search, start
from .settings import Settings


def build_router() -> Router:
    root = Router()

    # Подключаем все роутеры в нужном порядке
    for r in (
        start.build_router(),
        help.router,
        search.router,
        history.router,
        favorites.router,
        alerts.router,
    ):
        root.include_router(r)

    return root


async def _run_async() -> None:
    log = logging.getLogger(__name__)
    settings = Settings.from_env()
    api = ApiClient(settings.api_base_url, settings.service_token)
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    # Middleware для прокидывания ApiClient в хендлеры через kwargs

    class ApiMiddleware:
        def __init__(self, api: ApiClient):
            self.api = api

        async def __call__(self, handler, event, data):
            data["api"] = self.api
            return await handler(event, data)

    dp.update.outer_middleware(ApiMiddleware(api))

    dp.include_router(build_router())
    log.info("Bot starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await api.close()
        log.info("Bot stopped")


def run() -> None:
    asyncio.run(_run_async())
