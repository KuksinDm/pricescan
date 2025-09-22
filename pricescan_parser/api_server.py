import os
import sys

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Добавляем пути к парсерам
sys.path.append(os.path.join(os.path.dirname(__file__), "bs"))
sys.path.append(os.path.join(os.path.dirname(__file__), "req"))

from ghbs.client import HttpClient
from ghbs.parse_category import parse_category_page
from ghbs.parse_product import parse_product_page
from main import WildberriesParser

app = FastAPI(title="PriceScan Parser API", version="2.0.0")


class ParseProductRequest(BaseModel):
    url: str
    parser_type: str = "beautifulsoup"  # beautifulsoup, api_json


class SearchRequest(BaseModel):
    query: str
    limit: int = 50
    shop: str = "hobbygames"  # hobbygames, wildberries


@app.post("/parse/product")
async def parse_product(request: ParseProductRequest):
    """Парсинг конкретного товара"""
    try:
        if request.parser_type == "beautifulsoup":
            # HobbyGames через BeautifulSoup
            client = HttpClient()
            html = client.get_text(request.url)
            result = parse_product_page(html, request.url)
            return result
        else:
            return {"error": "Unsupported parser type"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse/search")
async def search_products(request: SearchRequest):
    """Поиск товаров"""
    try:
        if request.shop == "hobbygames":
            # HobbyGames через категорию
            client = HttpClient()
            category_url = "https://hobbygames.ru/nastolnye-igry/"
            html = client.get_text(category_url)
            products = parse_category_page(html, category_url)
            return {"products": products[: request.limit]}

        elif request.shop == "wildberries":
            # Wildberries через API
            parser = WildberriesParser()
            products = await parser.get_board_games_data(limit=request.limit)
            # Конвертируем в dict
            return {"products": [p.model_dump() for p in products]}

        else:
            return {"products": []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pricescan-parser-v2"}


@app.get("/parsers")
async def list_parsers():
    """Список доступных парсеров"""
    return {
        "parsers": {
            "hobbygames": {
                "type": "beautifulsoup",
                "description": "HobbyGames.ru парсер через BeautifulSoup",
            },
            "wildberries": {
                "type": "api_json",
                "description": "Wildberries парсер через JSON API",
            },
        }
    }
