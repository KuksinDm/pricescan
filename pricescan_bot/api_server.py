import logging
from typing import Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from .settings import Settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PriceScan Bot API",
    version="1.0.0",
    description="API для отправки уведомлений пользователям Telegram бота",
)

# Глобальные переменные для бота
bot: Optional[Bot] = None
settings: Optional[Settings] = None


class AlertNotification(BaseModel):
    """Модель для уведомления о срабатывании алерта"""

    user_id: int
    product_id: int
    price: float
    url: str
    alert_id: int


@app.on_event("startup")
async def startup_event():
    """Инициализация бота при запуске API сервера"""
    global bot, settings
    settings = Settings.from_env()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    logger.info("Bot API server started")


@app.on_event("shutdown")
async def shutdown_event():
    """Закрытие бота при остановке API сервера"""
    global bot
    if bot:
        await bot.session.close()
    logger.info("Bot API server stopped")


def verify_service_token(x_service_token: str = Header(None)) -> bool:
    """Проверка сервисного токена"""
    if not settings:
        raise HTTPException(status_code=500, detail="Server not initialized")

    if not x_service_token or x_service_token != settings.service_token:
        raise HTTPException(status_code=401, detail="Invalid service token")

    return True


@app.post("/send_alert")
async def send_alert(
    alert_data: AlertNotification, _: bool = Header(None, alias="X-Service-Token")
):
    """Отправка уведомления о срабатывании алерта пользователю"""
    # Проверяем сервисный токен
    if not verify_service_token():
        return {"success": False, "error": "Unauthorized"}

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

        logger.info(
            f"Alert sent to user {alert_data.user_id} for product {alert_data.product_id} "
            f"with price {alert_data.price}"
        )

        return {"success": True, "message": "Alert sent successfully"}

    except Exception as e:
        logger.error(f"Failed to send alert to user {alert_data.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send alert: {str(e)}")


@app.get("/health")
async def health_check():
    """Проверка здоровья API сервера"""
    return {
        "status": "ok",
        "service": "pricescan-bot-api",
        "bot_connected": bot is not None,
    }


@app.post("/send_message")
async def send_message(
    user_id: int,
    message: str,
    parse_mode: str = "HTML",
    _: bool = Header(None, alias="X-Service-Token"),
):
    """Универсальная отправка сообщения пользователю"""
    # Проверяем сервисный токен
    if not verify_service_token():
        return {"success": False, "error": "Unauthorized"}

    if not bot:
        raise HTTPException(status_code=500, detail="Bot not initialized")

    try:
        await bot.send_message(chat_id=user_id, text=message, parse_mode=parse_mode)

        logger.info(f"Message sent to user {user_id}")
        return {"success": True, "message": "Message sent successfully"}

    except Exception as e:
        logger.error(f"Failed to send message to user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
