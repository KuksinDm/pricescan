# pricescan_playwright/api_server.py
import logging
from contextlib import asynccontextmanager
from parser.playwright_parser import PlaywrightParser

from container import container
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from logging_config import setup_logging

from shared_models import CatalogRequest, CatalogResponse, ParseRequest, ParseResponse

setup_logging()
logger = logging.getLogger("parser_results")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Playwright Parser API starting up...")
    await container.initialize()
    logger.info("Parser container initialized")

    yield

    logger.info("Playwright Parser API shutting down...")
    await container.cleanup()
    logger.info("Parser resources cleaned up")


def create_app() -> FastAPI:
    """Создание FastAPI приложения"""
    app = FastAPI(
        title="PriceScan Playwright Parser API",
        version="3.0.0",
        description="Универсальный API для парсинга товаров через Playwright",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Внутренняя ошибка сервера",
            "detail": str(exc) if logger.level <= logging.DEBUG else None,
        },
    )


@app.post("/parse/product", response_model=ParseResponse)
async def parse_product(request: ParseRequest):
    """Парсинг конкретного товара по URL"""
    try:
        logger.info(
            f"parse_product called: url={request.url}, shop_url={request.shop_url}"
        )

        # Создаем парсер с DI
        parser = PlaywrightParser(container.browser_client, container.data_extractor)

        # Формируем полный URL
        if request.url.startswith("http"):
            full_url = request.url
        else:
            base_url = request.shop_url or "https://www.mosigra.ru"
            full_url = f"{base_url.rstrip('/')}/{request.url.lstrip('/')}"

        product = await parser.parse_product(full_url)

        if product:
            return ParseResponse(
                success=True, data=product, shop_name=request.shop_name
            )
        return ParseResponse(
            success=False,
            error="Не удалось спарсить товар",
            shop_name=request.shop_name,
        )
    except Exception as e:
        logger.exception("parse_product failed: %s", e)
        return ParseResponse(success=False, error=str(e), shop_name=request.shop_name)


@app.post("/parse/catalog", response_model=CatalogResponse)
async def parse_catalog(request: CatalogRequest):
    """Парсинг каталога магазина"""
    try:
        logger.info(
            f"parse_catalog called: shop_url={request.shop_url}, limit={request.limit}"
        )

        # Создаем парсер с DI
        parser = PlaywrightParser(container.browser_client, container.data_extractor)

        products = await parser.parse_catalog(
            request.shop_url,
            request.limit,
            page_start=request.page_start,
            max_pages=request.max_pages,
        )

        return CatalogResponse(
            success=True, products=products, total_found=len(products), failed_urls=0
        )
    except Exception as e:
        logger.exception("parse_catalog failed: %s", e)
        return CatalogResponse(
            success=False, products=[], total_found=0, failed_urls=0, error=str(e)
        )


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok",
        "service": "pricescan-playwright-parser",
        "version": "3.0.0",
        "parser_type": "playwright",
    }
