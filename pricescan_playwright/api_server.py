import logging
from parser.playwright_parser import PlaywrightParser

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from shared_models import (
    CatalogRequest,
    CatalogResponse,
    ParseRequest,
    ParseResponse,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="PriceScan Playwright Parser API",
    version="2.0.0",
    description="Универсальный API для парсинга товаров через Playwright",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


@app.post("/parse/product", response_model=ParseResponse)
async def parse_product(request: ParseRequest):
    """Парсинг конкретного товара"""
    try:
        logger.info(f"Получен запрос на парсинг товара: {request.url}")

        parser = PlaywrightParser(base_url=request.shop_url)
        product_data = await parser.parse_product(request.url)

        if product_data:
            return ParseResponse(
                success=True, data=product_data, shop_name=request.shop_name
            )
        else:
            return ParseResponse(
                success=False,
                error="Не удалось спарсить товар",
                shop_name=request.shop_name,
            )

    except Exception as e:
        logger.error(f"Ошибка при парсинге товара: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse/catalog", response_model=CatalogResponse)
async def parse_catalog(request: CatalogRequest):
    """Парсинг каталога магазина"""
    try:
        logger.info(f"Получен запрос на парсинг каталога: {request.shop_url}")

        parser = PlaywrightParser(base_url=request.shop_url)
        products = await parser.parse_catalog(request.shop_url, request.limit)

        return CatalogResponse(
            success=True,
            products=products,
            total_found=len(products),
            failed_urls=0,
        )

    except Exception as e:
        logger.error(f"Ошибка при парсинге каталога: {e}")
        return CatalogResponse(
            success=False,
            products=[],
            total_found=0,
            failed_urls=0,
            error=str(e),
        )


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok",
        "service": "pricescan-playwright-parser",
        "version": "2.0.0",
    }


@app.get("/parsers")
async def list_parsers():
    return {
        "parsers": {
            "playwright": {
                "type": "playwright",
                "description": "Универсальный парсер через Playwright",
                "supported_operations": ["parse_product", "parse_catalog"],
            }
        }
    }


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "PriceScan Playwright Parser API",
        "version": "2.0.0",
        "docs": "/docs",
    }
