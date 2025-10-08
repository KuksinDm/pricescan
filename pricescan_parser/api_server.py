import logging
import time
from contextlib import asynccontextmanager
from parser.beautifulsoup_parser import BeautifulSoupParser

from container import container
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from logging_config import get_results_logger, setup_logging

from shared_models import (
    CatalogRequest,
    CatalogResponse,
    ParseRequest,
    ParseResponse,
)

setup_logging()
logger = logging.getLogger(__name__)
results_logger = get_results_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PriceScan Parser API starting up...")
    await container.initialize()
    logger.info("Parser container initialized")

    yield

    logger.info("PriceScan Parser API shutting down...")
    await container.cleanup()
    logger.info("Parser resources cleaned up")


def create_app() -> FastAPI:
    app = FastAPI(
        title="PriceScan Parser API",
        version="3.0.0",
        description="Парсинг витрины HobbyGames, страницы каталога "
        "формируются через ?page=1&results_per_page=30",
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
    try:
        results_logger.info("=== BEAUTIFULSOUP API RECEIVED REQUEST ===")
        results_logger.info(
            f"url={request.url}, shop_url={request.shop_url}"
        )

        parser = BeautifulSoupParser(container.http_client, container.data_extractor)

        if request.url.startswith("http"):
            full_url = request.url
        else:
            base_url = request.shop_url or "https://hobbygames.ru"
            full_url = f"{base_url.rstrip('/')}/{request.url.lstrip('/')}"

        results_logger.info(f"Parsing product with full URL: {full_url}")
        product = await parser.parse_product(full_url)

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

        parser = BeautifulSoupParser(container.http_client, container.data_extractor)

        results_logger.info("Parser service ready, starting catalog parsing...")
        products = await parser.parse_catalog(
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
    logger.debug("=== HEALTH CHECK CALLED ===")
    return {
        "status": "ok",
        "service": "pricescan-parser",
        "version": "3.0.0",
        "parser_type": "beautifulsoup",
        "uptime": "running",
    }
