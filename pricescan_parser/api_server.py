import logging
from parser import BeautifulSoupParser

from fastapi import FastAPI

from shared_models import (
    CatalogRequest,
    CatalogResponse,
    ParseRequest,
    ParseResponse,
)

logger = logging.getLogger("parser_results")

app = FastAPI(
    title="PriceScan Parser API",
    version="3.0.0",
    description="Универсальный API для парсинга товаров",
)


@app.post("/parse/product", response_model=ParseResponse)
async def parse_product(request: ParseRequest):
    """Парсинг конкретного товара"""
    try:
        logger.info("=== BEAUTIFULSOUP API RECEIVED REQUEST ===")
        logger.info(
            f"parse_product called: parser_type={request.parser_type}, url={request.url}, shop_url={request.shop_url}"
        )

        # BeautifulSoup парсер обрабатывает ВСЕ запросы
        parser = BeautifulSoupParser(
            base_url=request.shop_url or "https://hobbygames.ru"
        )

        # Формируем полный URL
        if request.url.startswith("http"):
            full_url = request.url
        else:
            base_url = request.shop_url or "https://hobbygames.ru"
            full_url = f"{base_url.rstrip('/')}/{request.url.lstrip('/')}"

        logger.info(f"Parsing product with full URL: {full_url}")
        product = parser.parse_product(full_url)

        if product:
            logger.info(f"Successfully parsed product: {product.title}")
            return ParseResponse(
                success=True, data=product, shop_name=request.shop_name
            )
        else:
            logger.warning(f"Failed to parse product from: {full_url}")
            return ParseResponse(
                success=False,
                error="Не удалось спарсить товар",
                shop_name=request.shop_name,
            )

    except Exception as e:
        logger.error("=== BEAUTIFULSOUP API ERROR ===")
        logger.error(f"Error in parse_product: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return ParseResponse(success=False, error=str(e), shop_name=request.shop_name)


@app.post("/parse/catalog", response_model=CatalogResponse)
async def parse_catalog(request: CatalogRequest):
    """Парсинг каталога магазина"""
    try:
        logger.info("=== BEAUTIFULSOUP API RECEIVED REQUEST ===")
        logger.info(
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

        base_url = request.shop_url.rstrip("/")
        logger.info(f"Creating parser with base_url: {base_url}")
        parser = BeautifulSoupParser(base_url=base_url)

        logger.info("Parser created successfully, starting catalog parsing...")
        products = parser.parse_catalog(request.shop_url, request.limit)

        logger.info(f"Catalog parsing completed: found {len(products)} products")
        return CatalogResponse(
            success=True,
            products=products,
            total_found=len(products),
            failed_urls=0,
        )

    except Exception as e:
        logger.error("=== BEAUTIFULSOUP API ERROR ===")
        logger.error(f"Error in parse_catalog: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return CatalogResponse(
            success=False,
            products=[],
            total_found=0,
            failed_urls=0,
            error=str(e),
        )


@app.get("/health")
async def health_check():
    logger.info("=== HEALTH CHECK CALLED ===")
    return {"status": "ok", "service": "pricescan-parser-v3"}


@app.get("/test")
async def test_endpoint():
    logger.info("=== TEST ENDPOINT CALLED ===")
    try:
        # Тестируем импорты
        from parser import BeautifulSoupParser

        # Тестируем создание парсера
        parser = BeautifulSoupParser(base_url="https://hobbygames.ru")

        return {"status": "ok", "message": "All imports and parser creation successful"}
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}


@app.get("/parsers")
async def list_parsers():
    """Список доступных парсеров"""
    return {
        "parsers": {
            "hobbygames": {
                "type": "beautifulsoup",
                "description": "HobbyGames.ru парсер через BeautifulSoup",
                "base_url": "https://hobbygames.ru",
            },
        }
    }
