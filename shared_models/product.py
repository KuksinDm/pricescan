from typing import Optional

from pydantic import BaseModel, Field


class ProductData(BaseModel):
    """Единая модель товара для всех парсеров - совместима с Django моделями"""

    title: str = Field(..., description="Название товара")
    url: str = Field(..., description="URL товара")
    price_rub: Optional[int] = Field(None, description="Цена в рублях")
    manufacturer: Optional[str] = Field(None, description="Производитель/издатель")
    year: Optional[int] = Field(None, description="Год выпуска")
    players: Optional[str] = Field(
        None, description="Количество игроков (например: '1-4')"
    )
    play_time: Optional[str] = Field(
        None, description="Время игры (например: '60-120 минут')"
    )
    age: Optional[str] = Field(
        None, description="Возрастные ограничения (например: '14+')"
    )
    description: Optional[str] = Field(None, description="Описание товара")
    external_id: Optional[str] = Field(None, description="Внешний ID товара")
    image_url: Optional[str] = Field(None, description="URL изображения")

    def to_django_format(self) -> dict:
        """Преобразование в формат для Django моделей"""
        return {
            "title": self.title,
            "url": self.url,
            "price_rub": self.price_rub,
            "manufacturer": self.manufacturer,
            "year": self.year,
            "players": self.players,
            "play_time": self.play_time,
            "age": self.age,
            "description": self.description,
            "external_id": self.external_id,
            "image_url": self.image_url,
        }
