from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ProductInfo(BaseModel):
    """Базовая информация о товаре с HobbyGames.ru"""

    title: str
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None  # если есть скидка
    currency: str = "RUB"
    availability: str
    is_available: bool = True
    url: HttpUrl
    image_url: Optional[HttpUrl] = None

    # Дополнительные поля для настольных игр
    players_min: Optional[int] = None
    players_max: Optional[int] = None
    playtime_min: Optional[int] = None
    age_min: Optional[int] = None

    # Метаданные
    category: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None

    # Добавить новые поля
    author: Optional[str] = None
    publisher: Optional[str] = None


class SearchResult(BaseModel):
    """Результат поиска товаров"""

    query: str
    total_found: int
    page: int = 1
    per_page: int = 20
    products: List[ProductInfo] = Field(default_factory=list)


class CategoryInfo(BaseModel):
    """Информация о категории товаров"""

    name: str
    slug: str
    url: HttpUrl
    products_count: Optional[int] = None


class ParsingResult(BaseModel):
    """Результат парсинга"""

    success: bool
    error_message: Optional[str] = None
    products: List[ProductInfo] = Field(default_factory=list)
    total_parsed: int = 0
