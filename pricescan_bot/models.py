from pydantic import BaseModel


class AlertNotification(BaseModel):
    user_id: int
    product_id: int
    price: float
    currency: str
    url: str
    shop_name: str
    alert_id: int


class CustomMessage(BaseModel):
    user_id: int
    message: str
    parse_mode: str = "HTML"


class HealthResponse(BaseModel):
    status: str
    service: str
    bot_connected: bool
    dispatcher_ready: bool


class RootResponse(BaseModel):
    message: str
    version: str
    endpoints: dict
