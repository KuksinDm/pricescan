from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from .api import ApiClient
from .handlers import alerts, discounts, favorites, help, search, start
from .settings import Settings


class BotContainer:
    """Dependency Injection контейнер для бота"""
    def __init__(self):
        self._settings: Optional[Settings] = None
        self._bot: Optional[Bot] = None
        self._dispatcher: Optional[Dispatcher] = None
        self._api_client: Optional[ApiClient] = None

    async def initialize(self):
        self._settings = Settings.from_env()
        self._api_client = ApiClient(
            self._settings.api_base_url, self._settings.service_token
        )
        self._bot = Bot(
            token=self._settings.bot_token,
            default=DefaultBotProperties(parse_mode="HTML"),
        )
        self._dispatcher = Dispatcher()

        self._setup_dispatcher()

    def _setup_dispatcher(self):

        class ApiMiddleware:
            def __init__(self, container: "BotContainer"):
                self.container = container

            async def __call__(self, handler, event, data):
                data["container"] = self.container
                return await handler(event, data)

        self._dispatcher.update.outer_middleware(ApiMiddleware(self))

        for router_module in (
            start.router,
            help.router,
            search.router,
            discounts.router,
            favorites.router,
            alerts.router,
        ):
            self._dispatcher.include_router(router_module)

    @property
    def settings(self) -> Settings:
        if not self._settings:
            raise RuntimeError("Container not initialized")
        return self._settings

    @property
    def bot(self) -> Bot:
        if not self._bot:
            raise RuntimeError("Container not initialized")
        return self._bot

    @property
    def dispatcher(self) -> Dispatcher:
        if not self._dispatcher:
            raise RuntimeError("Container not initialized")
        return self._dispatcher

    @property
    def api_client(self) -> ApiClient:
        if not self._api_client:
            raise RuntimeError("Container not initialized")
        return self._api_client

    async def cleanup(self):
        if self._api_client:
            await self._api_client.close()
        if self._bot:
            await self._bot.session.close()


container = BotContainer()
