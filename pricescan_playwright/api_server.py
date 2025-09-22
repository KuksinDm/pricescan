import logging

from fastapi import FastAPI, HTTPException
from main import MosigraParser
from pydantic import BaseModel

app = FastAPI(title="PriceScan Playwright Parser API", version="1.0.0")

logger = logging.getLogger(__name__)


class ParseProductRequest(BaseModel):
    url: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 50
    max_pages: int = 2
    max_products: int = 20


@app.post("/parse/product")
async def parse_product(request: ParseProductRequest):
    """Парсинг конкретного товара через Playwright"""
    try:
        parser = MosigraParser()
        browser, page = await parser.start_browser()

        try:
            product = await parser.parse_product_card(page, request.url)
            if product:
                return product.model_dump()
            else:
                raise HTTPException(
                    status_code=404, detail="Товар не найден или не удалось спарсить"
                )

        finally:
            await browser.close()
            if parser.playwright:
                await parser.playwright.stop()

    except Exception as e:
        logger.error(f"Parse product error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse/search")
async def search_products(request: SearchRequest):
    """Поиск и парсинг товаров через Playwright"""
    try:
        parser = MosigraParser()

        # Запускаем парсинг
        await parser.run(max_pages=request.max_pages, max_products=request.max_products)

        # Возвращаем результаты
        products = [product.model_dump() for product in parser.products]

        return {
            "products": products,
            "total_found": len(products),
            "failed_urls": len(parser.failed_urls),
        }

    except Exception as e:
        logger.error(f"Search products error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pricescan-playwright-parser"}


@app.get("/parsers")
async def list_parsers():
    """Список доступных парсеров"""
    return {
        "parsers": {
            "mosigra": {
                "type": "playwright",
                "description": "Mosigra.ru парсер через Playwright",
                "base_url": "https://www.mosigra.ru",
            }
        }
    }
