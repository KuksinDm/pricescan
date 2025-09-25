import logging
from typing import List, Optional

import httpx

from shared_models import ProductData


class ApiJsonParser:
    """Универсальный API JSON парсер для работы с открытыми API"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def parse_product(self, product_id: str) -> Optional[ProductData]:
        """Парсинг одного товара по ID"""
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
                url = f"{self.base_url}/products/{product_id}"
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                return self._parse_product_data(data)

        except Exception as e:
            self.logger.error(f"Ошибка при парсинге товара {product_id}: {e}")
            return None

    async def parse_catalog(self, shop_url: str, limit: int = 100) -> List[ProductData]:
        """Парсинг каталога магазина"""
        try:
            # Для Wildberries используем их API
            if "wildberries" in shop_url:
                return await self._parse_wildberries_catalog(shop_url, limit)
            else:
                # Для не-API магазинов возвращаем пустой список
                self.logger.warning(
                    f"API JSON парсер не поддерживает HTML каталог: {shop_url}"
                )
                return []
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге каталога: {e}")
            return []

    async def _parse_wildberries_catalog(
        self, shop_url: str, limit: int
    ) -> List[ProductData]:
        """Парсинг каталога Wildberries"""
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
                # Используем API каталога Wildberries
                url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
                params = {
                    "appType": 1,
                    "curr": "rub",
                    "dest": -1257786,
                    "query": "настольная игра",
                    "resultset": "catalog",
                    "sort": "popular",
                    "spp": 30,
                }

                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                products = []

                if "data" in data and "products" in data["data"]:
                    items = data["data"]["products"]
                    for item in items[:limit]:
                        product = self._parse_wildberries_product(item)
                        if product:
                            products.append(product)

                return products
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге каталога Wildberries: {e}")
            return []

    def _parse_wildberries_product(self, item: dict) -> Optional[ProductData]:
        """Парсинг товара Wildberries"""
        try:
            product_id = item.get("id", 0)
            title = item.get("name", "").strip()

            if not title or not product_id:
                return None

            url = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

            # Цена из sizes[0].price.product (в копейках -> рубли)
            price_rub = None
            if "sizes" in item and item["sizes"] and item["sizes"][0].get("price"):
                price_data = item["sizes"][0]["price"]
                if "product" in price_data:
                    price_rub = price_data["product"] // 100

            manufacturer = item.get("brand", "").strip() or None

            return ProductData(
                title=title,
                url=url,
                price_rub=price_rub,
                manufacturer=manufacturer,
            )

        except Exception as e:
            self.logger.error(f"Ошибка при парсинге товара Wildberries: {e}")
            return None

    def _parse_product_data(self, data: dict) -> Optional[ProductData]:
        """Универсальный парсинг данных товара"""
        try:
            return ProductData(
                title=data.get("title", data.get("name", "")),
                url=data.get("url", data.get("link", "")),
                price_rub=data.get("price_rub", data.get("price")),
                manufacturer=data.get("manufacturer", data.get("brand")),
                year=data.get("year"),
                players=data.get("players"),
                play_time=data.get("play_time"),
                age=data.get("age"),
                description=data.get("description"),
                external_id=data.get("id", data.get("external_id")),
                image_url=data.get("image_url", data.get("image")),
            )
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге данных товара: {e}")
            return None
