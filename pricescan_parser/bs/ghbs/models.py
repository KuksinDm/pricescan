from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    title: str
    url: str
    price_rub: Optional[int]
    manufacturer: Optional[str]  # производитель
    year: Optional[int]  # год выпуска
    players: Optional[str]  # количество игроков "1-2"
    play_time: Optional[str]  # время партии "60-120"
    age: Optional[str]  # возраст "14+"
    description: Optional[str]
