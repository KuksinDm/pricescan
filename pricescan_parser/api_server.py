import logging
import time
from contextlib import asynccontextmanager
from parser import BeautifulSoupParser

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from logging_config import get_results_logger, setup_logging
from settings import ParserSettings

from shared_models import (
    CatalogRequest,
    CatalogResponse,
    ParseRequest,
    ParseResponse,
)

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)
results_logger = get_results_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("PriceScan Parser API starting up...")
    yield
    logger.info("PriceScan Parser API shutting down...")


def create_app() -> FastAPI:
    """Создание FastAPI приложения"""
    app = FastAPI(
        title="PriceScan Parser API",
        version="3.0.0",
        description="Универсальный API для парсинга товаров через BeautifulSoup",
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

    # Middleware для логирования запросов
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )

        return response

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
    """Парсинг конкретного товара"""
    try:
        results_logger.info("=== BEAUTIFULSOUP API RECEIVED REQUEST ===")
        results_logger.info(
            f"parse_product called: parser_type={request.parser_type}, "
            f"url={request.url}, shop_url={request.shop_url}"
        )

        # Создаем настройки парсера
        settings = ParserSettings(base_url=request.shop_url or "https://hobbygames.ru")

        # Создаем парсер с настройками
        parser = BeautifulSoupParser(settings)

        # Формируем полный URL
        if request.url.startswith("http"):
            full_url = request.url
        else:
            base_url = request.shop_url or "https://hobbygames.ru"
            full_url = f"{base_url.rstrip('/')}/{request.url.lstrip('/')}"

        results_logger.info(f"Parsing product with full URL: {full_url}")
        product = parser.parse_product(full_url)

        if product:
            results_logger.info(f"Successfully parsed product: {product.title}")
            return ParseResponse(
                success=True, data=product, shop_name=request.shop_name
            )
        else:
            results_logger.warning(f"Failed to parse product from: {full_url}")
            return ParseResponse(
                success=False,
                error="Не удалось спарсить товар",
                shop_name=request.shop_name,
            )

    except Exception as e:
        logger.error("=== BEAUTIFULSOUP API ERROR ===")
        logger.error(f"Error in parse_product: {str(e)}", exc_info=True)
        return ParseResponse(
            success=False,
            error=f"Ошибка парсинга: {str(e)}",
            shop_name=request.shop_name,
        )


@app.post("/parse/catalog", response_model=CatalogResponse)
async def parse_catalog(request: CatalogRequest):
    """Парсинг каталога магазина"""
    try:
        results_logger.info("=== BEAUTIFULSOUP API RECEIVED CATALOG REQUEST ===")
        results_logger.info(
            f"parse_catalog called: shop_url={request.shop_url}, limit={request.limit}"
        )

        if not request.shop_url:
            logger.error("shop_url is empty or None")
            return CatalogResponse(
                success=False,
                products=[],
                total_found=0,
                failed_urls=0,
                error="shop_url is required",
            )

        # Создаем настройки парсера
        settings = ParserSettings(base_url=request.shop_url.rstrip("/"))

        # Создаем парсер с настройками
        parser = BeautifulSoupParser(settings)

        results_logger.info("Parser created successfully, starting catalog parsing...")
        products = parser.parse_catalog(
            request.shop_url,
            request.limit,
            getattr(request, "page_start", 1),
            getattr(request, "max_pages", None),
            getattr(request, "detail", True),
        )

        results_logger.info(
            f"Catalog parsing completed: found {len(products)} products"
        )
        return CatalogResponse(
            success=True,
            products=products,
            total_found=len(products),
            failed_urls=0,
        )

    except Exception as e:
        logger.error("=== BEAUTIFULSOUP API ERROR ===")
        logger.error(f"Error in parse_catalog: {str(e)}", exc_info=True)
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
    logger.info("=== HEALTH CHECK CALLED ===")
    return {
        "status": "ok",
        "service": "pricescan-parser",
        "version": "3.0.0",
        "parser_type": "beautifulsoup",
        "uptime": "running",
    }


@app.get("/test")
async def test_endpoint():
    """Тестовый эндпоинт для проверки работоспособности"""
    logger.info("=== TEST ENDPOINT CALLED ===")
    try:
        # Тестируем создание парсера
        settings = ParserSettings(base_url="https://hobbygames.ru")
        parser = BeautifulSoupParser(settings)

        return {
            "status": "ok",
            "message": "All imports and parser creation successful",
            "parser_type": "beautifulsoup",
        }
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@app.get("/parsers")
async def list_parsers():
    """Список доступных парсеров"""
    return {
        "parsers": {
            "beautifulsoup": {
                "type": "beautifulsoup",
                "description": "Универсальный парсер через BeautifulSoup для HTML сайтов",
                "supported_operations": ["parse_product", "parse_catalog"],
                "supported_sites": [
                    "hobbygames.ru",
                    "mosigra.ru",
                    "igrotime.ru",
                    "и другие HTML сайты",
                ],
                "features": [
                    "Поддержка HobbyGames.ru",
                    "Извлечение производителей и категорий",
                    "Парсинг игровых характеристик",
                    "Обработка каталогов",
                ],
            }
        }
    }


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "PriceScan Parser API",
        "version": "3.0.0",
        "description": "Универсальный парсер для HTML сайтов",
        "docs": "/docs",
        "health": "/health",
        "parsers": "/parsers",
        "test": "/test",
    }
