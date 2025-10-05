from pydantic import BaseModel


class AlertNotification(BaseModel):
    """Модель для уведомления о срабатывании алерта"""

    user_id: int
    product_id: int
    price: float
    currency: str
    url: str
    shop_name: str
    alert_id: int


class CustomMessage(BaseModel):
    """Модель для произвольного сообщения"""

    user_id: int
    message: str
    parse_mode: str = "HTML"


class HealthResponse(BaseModel):
    """Модель для ответа health check"""

    status: str
    service: str
    bot_connected: bool
    dispatcher_ready: bool


class RootResponse(BaseModel):
    """Модель для корневого эндпоинта"""

    message: str
    version: str
    endpoints: dict
