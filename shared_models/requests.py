from typing import Optional

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    """Запрос на парсинг товара - универсальная модель для всех парсеров"""

    url: str = Field(..., description="URL товара для парсинга")
    parser_type: Optional[str] = Field(
        None, description="Тип парсера (для совместимости)"
    )
    shop_name: str = Field(default="Unknown", description="Название магазина")
    shop_url: Optional[str] = Field(
        None, description="URL магазина (для совместимости)"
    )


class CatalogRequest(BaseModel):
    shop_url: str = Field(..., description="URL каталога магазина")
    limit: int = Field(default=100, description="Максимальное количество товаров")
    shop_name: str = Field(default="Unknown", description="Название магазина")
    parser_type: Optional[str] = Field(
        None, description="Тип парсера: beautifulsoup, playwright"
    )
