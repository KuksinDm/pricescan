"""
Сервис для работы с парсерами
Обеспечивает единый интерфейс для всех типов парсеров
"""

import logging
from typing import Dict, List, Optional

import httpx

from ..models import Shop

logger = logging.getLogger(__name__)


class ParserService:
    """Единый сервис для работы со всеми парсерами"""

    PARSER_URLS = {
        "beautifulsoup": "http://pricescan_parser:8000",
        "playwright": "http://pricescan_playwright:8000",
        "api_json": "http://pricescan_parser:8000",
    }

    @classmethod
    async def parse_products(
        cls,
        shop: Shop,
        query: str = "настольные игры",
        max_products: int = 50,
        category_url: str = None,
    ) -> List[Dict]:
        """
        Парсинг продуктов через соответствующий парсер

        Args:
            shop: Магазин для парсинга
            query: Поисковый запрос
            max_products: Максимальное количество продуктов
            category_url: URL категории (опционально)

        Returns:
            List[Dict]: Список продуктов в едином формате
        """
        parser_url = cls.PARSER_URLS.get(shop.parser_type)
        if not parser_url:
            raise ValueError(f"Неподдерживаемый тип парсера: {shop.parser_type}")

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                if shop.parser_type == "playwright":
                    # Playwright парсер
                    response = await client.post(
                        f"{parser_url}/parse/search",
                        json={
                            "query": query,
                            "limit": max_products,
                            "max_pages": 3,
                            "max_products": max_products,
                        },
                    )
                elif shop.parser_type == "beautifulsoup":
                    # BeautifulSoup парсер
                    response = await client.post(
                        f"{parser_url}/parse/search",
                        json={
                            "query": query,
                            "limit": max_products,
                            "shop": "hobbygames",
                        },
                    )
                elif shop.parser_type == "api_json":
                    # API JSON парсер
                    response = await client.post(
                        f"{parser_url}/parse/search",
                        json={
                            "query": query,
                            "limit": max_products,
                            "shop": "wildberries",
                        },
                    )
                else:
                    raise ValueError(
                        f"Неподдерживаемый тип парсера: {shop.parser_type}"
                    )

                response.raise_for_status()
                result = response.json()

                # Нормализуем данные в единый формат
                products = result.get("products", [])
                return cls._normalize_products_data(products, shop.parser_type)

        except Exception as e:
            logger.error(f"Ошибка парсинга через {shop.parser_type}: {e}")
            raise

    @classmethod
    async def parse_single_product(cls, shop: Shop, product_url: str) -> Optional[Dict]:
        """
        Парсинг одного продукта по URL

        Args:
            shop: Магазин
            product_url: URL продукта

        Returns:
            Dict: Данные продукта в едином формате или None
        """
        parser_url = cls.PARSER_URLS.get(shop.parser_type)
        if not parser_url:
            raise ValueError(f"Неподдерживаемый тип парсера: {shop.parser_type}")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{parser_url}/parse/product",
                    json={"url": product_url, "parser_type": shop.parser_type},
                )
                response.raise_for_status()
                result = response.json()

                # Нормализуем данные в единый формат
                return cls._normalize_product_data(result, shop.parser_type)

        except Exception as e:
            logger.error(
                f"Ошибка парсинга продукта {product_url} через {shop.parser_type}: {e}"
            )
            return None

    @classmethod
    def _normalize_products_data(
        cls, products: List[Dict], parser_type: str
    ) -> List[Dict]:
        """Нормализация данных продуктов в единый формат"""
        normalized = []

        for product in products:
            try:
                normalized_product = cls._normalize_product_data(product, parser_type)
                if normalized_product:
                    normalized.append(normalized_product)
            except Exception as e:
                logger.error(f"Ошибка нормализации продукта: {e}")
                continue

        return normalized

    @classmethod
    def _normalize_product_data(cls, product: Dict, parser_type: str) -> Optional[Dict]:
        """
        Нормализация данных одного продукта в единый формат

        Единый формат:
        {
            "title": str,
            "url": str,
            "price_rub": int,
            "manufacturer": str,
            "year": int,
            "players": str,
            "play_time": str,
            "age": str,
            "description": str,
            "image_url": str,
            "external_id": str
        }
        """
        try:
            normalized = {
                "title": product.get("title", "").strip(),
                "url": product.get("url", ""),
                "price_rub": product.get("price_rub"),
                "manufacturer": product.get("manufacturer"),
                "year": product.get("year"),
                "players": product.get("players"),
                "play_time": product.get("play_time"),
                "age": product.get("age"),
                "description": product.get("description", ""),
                "image_url": product.get("image_url", ""),
                "external_id": product.get("external_id", ""),
            }

            # Валидация обязательных полей
            if not normalized["title"]:
                return None

            return normalized

        except Exception as e:
            logger.error(f"Ошибка нормализации продукта: {e}")
            return None

    @classmethod
    async def health_check(cls) -> Dict[str, bool]:
        """Проверка здоровья всех парсеров"""
        health_status = {}

        for parser_type, url in cls.PARSER_URLS.items():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{url}/health")
                    health_status[parser_type] = response.status_code == 200
            except Exception:
                health_status[parser_type] = False

        return health_status
