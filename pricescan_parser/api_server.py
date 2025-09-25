from parser import ApiJsonParser, BeautifulSoupParser

from fastapi import FastAPI

from shared_models import (
    CatalogRequest,
    CatalogResponse,
    ParseRequest,
    ParseResponse,
)

app = FastAPI(
    title="PriceScan Parser API",
    version="3.0.0",
    description="Универсальный API для парсинга товаров",
)


@app.post("/parse/product", response_model=ParseResponse)
async def parse_product(request: ParseRequest):
    """Парсинг конкретного товара"""
    try:
        if request.parser_type == "beautifulsoup":
            # BeautifulSoup парсер
            parser = BeautifulSoupParser(
                base_url=request.shop_url or "https://hobbygames.ru"
            )

            # Формируем полный URL
            if request.url.startswith("http"):
                full_url = request.url
            else:
                base_url = request.shop_url or "https://hobbygames.ru"
                full_url = f"{base_url.rstrip('/')}/{request.url.lstrip('/')}"

            product = parser.parse_product(full_url)

            if product:
                return ParseResponse(
                    success=True, data=product, shop_name=request.shop_name
                )
            else:
                return ParseResponse(
                    success=False,
                    error="Не удалось спарсить товар",
                    shop_name=request.shop_name,
                )

        elif request.parser_type == "api_json":
            # API JSON парсер
            parser = ApiJsonParser(
                base_url=request.shop_url or "https://api.example.com"
            )
            # Извлекаем ID из URL только для API JSON парсера
            product_id = request.url.split("/")[-1]
            product = await parser.parse_product(product_id)

            if product:
                return ParseResponse(
                    success=True, data=product, shop_name=request.shop_name
                )
            else:
                return ParseResponse(
                    success=False,
                    error="Не удалось спарсить товар",
                    shop_name=request.shop_name,
                )
        else:
            return ParseResponse(
                success=False,
                error=f"Неподдерживаемый тип парсера: {request.parser_type}",
                shop_name=request.shop_name,
            )

    except Exception as e:
        return ParseResponse(success=False, error=str(e), shop_name=request.shop_name)


@app.post("/parse/catalog", response_model=CatalogResponse)
async def parse_catalog(request: CatalogRequest):
    """Парсинг каталога магазина"""
    try:
        # Используем parser_type из запроса
        if request.parser_type == "api_json":
            parser = ApiJsonParser(base_url=request.shop_url)
            products = await parser.parse_catalog(request.shop_url, request.limit)
        else:  # beautifulsoup по умолчанию
            parser = BeautifulSoupParser(base_url=request.shop_url)
            products = parser.parse_catalog(request.shop_url, request.limit)

        return CatalogResponse(
            success=True,
            products=products,
            total_found=len(products),
            failed_urls=0,
        )

    except Exception as e:
        return CatalogResponse(
            success=False,
            products=[],
            total_found=0,
            failed_urls=0,
            error=str(e),
        )


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pricescan-parser-v3"}


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
            "wildberries": {
                "type": "api_json",
                "description": "Wildberries парсер через JSON API",
                "base_url": "https://catalog.wb.ru",
            },
        }
    }
