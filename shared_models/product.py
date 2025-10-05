from typing import List, Optional

from pydantic import BaseModel, Field


class ProductData(BaseModel):
    """Единая модель товара для всех парсеров - совместима с Django моделями"""

    title: str = Field(..., description="Название товара")
    url: str = Field(..., description="URL товара")
    price_rub: Optional[int] = Field(None, description="Цена в рублях")

    # Множественные связи (убрать authors)
    manufacturers: List[str] = Field(
        default_factory=list, description="Список производителей/издателей"
    )
    categories: List[str] = Field(default_factory=list, description="Список категорий")

    # Игровые характеристики
    players: Optional[str] = Field(
        None, description="Количество игроков (например: '1-4')"
    )
    play_time: Optional[str] = Field(
        None, description="Время игры (например: '60-120 минут')"
    )
    age: Optional[str] = Field(
        None, description="Возрастные ограничения (например: '14+')"
    )

    def to_django_format(self) -> dict:
        """Преобразование в формат для Django моделей"""
        return {
            "title": self.title,
            "url": self.url,
            "price_rub": self.price_rub,
            "manufacturer": ", ".join(self.manufacturers)
            if self.manufacturers
            else None,
            "categories": ", ".join(self.categories) if self.categories else None,
            "players": self.players,
            "play_time": self.play_time,
            "age": self.age,
        }
