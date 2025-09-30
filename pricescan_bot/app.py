import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from .api import ApiClient
from .handlers import alerts, favorites, help, history, search, start
from .settings import Settings

# Глобальные переменные
bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None
api_client: Optional[ApiClient] = None
settings: Optional[Settings] = None


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


async def init_bot():
    """Инициализация бота и диспетчера"""
    global bot, dp, api_client, settings

    settings = Settings.from_env()
    api_client = ApiClient(settings.api_base_url, settings.service_token)
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Middleware для прокидывания ApiClient в хендлеры через kwargs
    class ApiMiddleware:
        def __init__(self, api: ApiClient):
            self.api = api

        async def __call__(self, handler, event, data):
            data["api"] = self.api
            return await handler(event, data)

    dp.update.outer_middleware(ApiMiddleware(api_client))
    dp.include_router(build_router())


# Pydantic модели для API
class AlertNotification(BaseModel):
    """Модель для уведомления о срабатывании алерта"""

    user_id: int
    product_id: int
    price: float
    url: str
    alert_id: int


class CustomMessage(BaseModel):
    """Модель для произвольного сообщения"""

    user_id: int
    message: str
    parse_mode: str = "HTML"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Инициализация бота
    await init_bot()

    # Запуск polling в фоне
    polling_task = asyncio.create_task(start_polling())

    yield

    # Остановка polling
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

    # Очистка ресурсов
    if api_client:
        await api_client.close()
    if bot:
        await bot.session.close()


def create_app() -> FastAPI:
    """Создание FastAPI приложения"""
    app = FastAPI(
        title="PriceScan Bot API",
        version="1.0.0",
        description="API для Telegram бота и отправки уведомлений",
        lifespan=lifespan,
    )

    return app


# Создаем FastAPI приложение
app = create_app()


# def verify_service_token(x_service_token: str = Header(None)) -> bool:
#     """Проверка сервисного токена"""
#     if not settings:
#         raise HTTPException(status_code=500, detail="Server not initialized")

#     if not x_service_token or x_service_token != settings.service_token:
#         raise HTTPException(status_code=401, detail="Invalid service token")

#     return True


@app.post("/send_alert")
async def send_alert_endpoint(
    alert_data: AlertNotification,
    x_service_token: str = Header(None, alias="X-Service-Token"),
):
    """Отправка уведомления о срабатывании алерта пользователю"""
    # Проверяем сервисный токен
    if not settings:
        raise HTTPException(status_code=500, detail="Server not initialized")

    if not x_service_token or x_service_token != settings.service_token:
        raise HTTPException(status_code=401, detail="Invalid service token")

    if not bot:
        raise HTTPException(status_code=500, detail="Bot not initialized")

    try:
        # Формируем сообщение для пользователя
        message_text = (
            "🚨 <b>Сработал алерт!</b>\n\n"
            f"💰 Цена снизилась до <b>{alert_data.price:.2f} ₽</b>\n"
            f"🛒 <a href='{alert_data.url}'>Перейти к товару</a>\n\n"
            "Подписка автоматически отключена."
        )

        # Отправляем сообщение пользователю
        await bot.send_message(
            chat_id=alert_data.user_id,
            text=message_text,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )

        logging.getLogger(__name__).info(
            f"Alert sent to user {alert_data.user_id} for product {alert_data.product_id} "
            f"with price {alert_data.price}"
        )

        return {"success": True, "message": "Alert sent successfully"}

    except Exception as e:
        logging.getLogger(__name__).error(
            f"Failed to send alert to user {alert_data.user_id}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to send alert: {str(e)}")



@app.post("/send_message")
async def send_message_endpoint(
    message_data: CustomMessage,
    x_service_token: str = Header(None, alias="X-Service-Token")
):
    """Универсальная отправка сообщения пользователю"""
    # Проверяем сервисный токен
    if not settings:
        raise HTTPException(status_code=500, detail="Server not initialized")

    if not x_service_token or x_service_token != settings.service_token:
        raise HTTPException(status_code=401, detail="Invalid service token")

    if not bot:
        raise HTTPException(status_code=500, detail="Bot not initialized")

    try:
        await bot.send_message(
            chat_id=message_data.user_id,
            text=message_data.message,
            parse_mode=message_data.parse_mode,
        )

        logging.getLogger(__name__).info(f"Message sent to user {message_data.user_id}")
        return {"success": True, "message": "Message sent successfully"}

    except Exception as e:
        logging.getLogger(__name__).error(
            f"Failed to send message to user {message_data.user_id}: {e}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@app.get("/health")
async def health_check():
    """Проверка здоровья API сервера"""
    return {
        "status": "ok",
        "service": "pricescan-bot-api",
        "bot_connected": bot is not None,
        "dispatcher_ready": dp is not None,
    }


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "PriceScan Bot API",
        "version": "1.0.0",
        "endpoints": {
            "send_alert": "/send_alert",
            "send_message": "/send_message",
            "health": "/health",
        },
    }


async def start_polling():
    """Запуск polling режима"""
    if not bot or not dp:
        await init_bot()

    logging.getLogger(__name__).info("Bot starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        if api_client:
            await api_client.close()
        logging.getLogger(__name__).info("Bot stopped")


def run_polling():
    """Запуск только polling (для разработки)"""
    asyncio.run(start_polling())


def run_api(host: str = "0.0.0.0", port: int = 8000):
    """Запуск API сервера"""
    uvicorn.run(app, host=host, port=port)


def run():
    """Запуск по умолчанию (API сервер)"""
    run_api()
