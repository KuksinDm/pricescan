"""
Парсер для HobbyGames.ru
"""

from .client import HobbyGamesClient
from .models import ParsingResult, ProductInfo, SearchResult
from .parser import BSParser, HobbyGamesParser

__all__ = [
    "HobbyGamesParser",
    "BSParser",
    "HobbyGamesClient",
    "ProductInfo",
    "SearchResult",
    "ParsingResult",
]
