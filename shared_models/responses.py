from typing import List, Optional

from pydantic import BaseModel, Field

from .product import ProductData


class ParseResponse(BaseModel):
    """Ответ парсера - универсальная модель для всех парсеров"""

    success: bool = Field(..., description="Успешность операции")
    data: Optional[ProductData] = Field(None, description="Данные товара")
    error: Optional[str] = Field(None, description="Сообщение об ошибке")
    shop_name: str = Field(default="Unknown", description="Название магазина")


class CatalogResponse(BaseModel):
    success: bool
    products: List[ProductData] = []
    total_found: int = 0
    failed_urls: Optional[int] = None
    error: Optional[str] = None
