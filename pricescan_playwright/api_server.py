import logging
from parser.playwright_parser import PlaywrightParser

from fastapi import FastAPI
from logging_config import setup_logging
from settings import PlaywrightSettings

from shared_models import CatalogRequest, CatalogResponse, ParseRequest, ParseResponse

setup_logging()
logger = logging.getLogger("parser_results")

app = FastAPI(
    title="Inwork Playwright Parser API",
    version="0.1.0",
    description="Временный парсер в стиле pricescan_parser",
)


@app.post("/parse/product", response_model=ParseResponse)
async def parse_product(request: ParseRequest):
    try:
        settings = PlaywrightSettings(
            base_url=request.shop_url or "https://www.mosigra.ru/nastolnye-igry"
        )
        parser = PlaywrightParser(settings)
        url = (
            request.url
            if request.url.startswith("http")
            else f"{settings.base_url.rstrip('/')}/{request.url.lstrip('/')}"
        )
        product = await parser.parse_product(url)
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
    try:
        settings = PlaywrightSettings(
            base_url=request.shop_url or "https://www.mosigra.ru/nastolnye-igry"
        )
        parser = PlaywrightParser(settings)
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
    return {"ok": True}
