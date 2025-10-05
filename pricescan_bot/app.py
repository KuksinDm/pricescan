import asyncio
import hmac
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Header, HTTPException

from .container import container
from .models import AlertNotification, CustomMessage, HealthResponse, RootResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Инициализация контейнера
    await container.initialize()
    logger.info("Bot container initialized")

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
    await container.cleanup()
    logger.info("Bot resources cleaned up")


def create_app() -> FastAPI:
    """Создание FastAPI приложения"""
    app = FastAPI(
        title="PriceScan Bot API",
        version="1.0.0",
        description="API для Telegram бота и отправки уведомлений",
        lifespan=lifespan,
    )
    return app


app = create_app()


def verify_service_token(
    x_service_token: str = Header(None, alias="X-Service-Token"),
) -> bool:
    """Проверка сервисного токена с защитой от timing attacks"""
    if not container.settings:
        raise HTTPException(status_code=500, detail="Server not initialized")

    if not hmac.compare_digest(x_service_token or "", container.settings.service_token):
        raise HTTPException(status_code=401, detail="Invalid service token")
    return True


async def _ensure_bot_ready():
    """Проверяет, что бот инициализирован"""
    if not container.bot:
        raise HTTPException(status_code=500, detail="Bot not initialized")


@app.post("/send_alert")
async def send_alert_endpoint(
    alert_data: AlertNotification,
    x_service_token: str = Header(None, alias="X-Service-Token"),
):
    """Отправка уведомления о срабатывании алерта пользователю"""
    verify_service_token(x_service_token)
    await _ensure_bot_ready()

    try:
        message_text = (
            "🚨 <b>Сработал алерт!</b>\n\n"
            f"💰 Цена снизилась до <b>{alert_data.price:.2f} {alert_data.currency}</b>\n"
            f"🏪 Магазин: <b>{alert_data.shop_name}</b>\n"
            f"🛒 <a href='{alert_data.url}'>Перейти к товару</a>\n\n"
            "Подписка автоматически отключена."
        )

        await container.bot.send_message(
            chat_id=alert_data.user_id,
            text=message_text,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )

        logger.info(
            f"Alert sent to user {alert_data.user_id} for product {alert_data.product_id}"
        )
        return {"success": True, "message": "Alert sent successfully"}

    except Exception as e:
        logger.error(f"Failed to send alert to user {alert_data.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send alert: {str(e)}")


@app.post("/send_message")
async def send_message_endpoint(
    message_data: CustomMessage,
    x_service_token: str = Header(None, alias="X-Service-Token"),
):
    """Универсальная отправка сообщения пользователю"""
    verify_service_token(x_service_token)
    await _ensure_bot_ready()

    try:
        await container.bot.send_message(
            chat_id=message_data.user_id,
            text=message_data.message,
            parse_mode=message_data.parse_mode,
        )
        logger.info(f"Message sent to user {message_data.user_id}")
        return {"success": True, "message": "Message sent successfully"}
    except Exception as e:
        logger.error(f"Failed to send message to user {message_data.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@app.get("/health")
async def health_check() -> HealthResponse:
    """Проверка здоровья API сервера"""
    return HealthResponse(
        status="ok",
        service="pricescan-bot-api",
        bot_connected=container.bot is not None,
        dispatcher_ready=container.dispatcher is not None,
    )


@app.get("/")
async def root() -> RootResponse:
    """Корневой эндпоинт"""
    return RootResponse(
        message="PriceScan Bot API",
        version="1.0.0",
        endpoints={
            "send_alert": "/send_alert",
            "send_message": "/send_message",
            "health": "/health",
        },
    )


async def start_polling():
    """Запуск polling режима"""
    logger.info("Bot starting polling...")
    try:
        await container.dispatcher.start_polling(container.bot)
    finally:
        await container.cleanup()
        logger.info("Bot stopped")


def run_polling():
    """Запуск только polling (для разработки)"""
    asyncio.run(start_polling())


def run_api(host: str = "0.0.0.0", port: int = 8000):
    """Запуск API сервера"""
    uvicorn.run(app, host=host, port=port)


def run():
    """Запуск по умолчанию (API сервер)"""
    run_api()
