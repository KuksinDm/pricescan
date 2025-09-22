import asyncio
import json
from typing import List, Optional

import httpx
from loguru import logger
from pydantic import BaseModel


class Product(BaseModel):
    title: str
    url: str
    price_rub: Optional[int] = None
    manufacturer: Optional[str] = None  # производитель (brand)


class WildberriesParser:
    """Парсер для получения данных о настольных играх с Wildberries через JSON API"""

    def __init__(self):
        self.base_url = "https://catalog.wb.ru"
        self.search_url = "https://search.wb.ru"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }

    async def get_board_games_data(
        self, page: int = 1, limit: int = 100
    ) -> List[Product]:
        """
        Получает данные о настольных играх

        Args:
            page: номер страницы
            limit: количество товаров на странице

        Returns:
            List[Product]: список продуктов
        """
        products = []

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
                # Используем рабочий API v5
                url = f"{self.search_url}/exactmatch/ru/common/v5/search"
                params = {
                    "appType": 1,
                    "curr": "rub",
                    "dest": -1257786,
                    "query": "настольная игра",
                    "resultset": "catalog",
                    "sort": "popular",
                    "spp": 30,
                }

                logger.info(f"Запрос к API: {url}")
                logger.info(f"Параметры: {params}")

                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                logger.info(
                    f"Получен ответ: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                )

                # Сохраняем полный ответ от API в файл для анализа
                with open("api_response_search.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info("Сохранен полный ответ API в файл api_response_search.json")

                # Извлекаем товары
                if "data" in data and "products" in data["data"]:
                    items = data["data"]["products"]
                    logger.info(f"Найдено товаров в ответе: {len(items)}")

                    for item in items[:limit]:
                        product = self._parse_product(item)
                        if product:
                            products.append(product)

                logger.info(f"Итого получено {len(products)} товаров")

        except Exception as e:
            logger.error(f"Ошибка при получении данных: {e}")

        return products

    def _parse_product(self, item: dict) -> Optional[Product]:
        """
        Парсит данные одного товара из реальных данных API

        Args:
            item: словарь с данными товара из API

        Returns:
            Product или None если не удалось распарсить
        """
        try:
            # Базовые данные
            product_id = item.get("id", 0)
            title = item.get("name", "").strip()

            if not title or not product_id:
                return None

            # URL товара
            url = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

            # Цена из sizes[0].price.product (в копейках -> рубли)
            price_rub = None
            if "sizes" in item and item["sizes"] and item["sizes"][0].get("price"):
                price_data = item["sizes"][0]["price"]
                if "product" in price_data:
                    price_rub = price_data["product"] // 100

            # Производитель/бренд
            manufacturer = item.get("brand", "").strip() or None

            return Product(
                title=title,
                url=url,
                price_rub=price_rub,
                manufacturer=manufacturer,
            )

        except Exception as e:
            logger.error(f"Ошибка при парсинге товара: {e}")
            logger.error(f"Структура товара: {item.keys()}")
            return None


async def main():
    """Основная функция для тестирования парсера"""
    logger.info("Запуск парсера Wildberries для настольных игр")

    parser = WildberriesParser()

    # Получаем товары
    products = await parser.get_board_games_data(page=1, limit=10)

    logger.info(f"Найдено товаров: {len(products)}")

    for i, product in enumerate(products, 1):
        print(f"\n{i}. {product.title}")
        print(f"   URL: {product.url}")
        print(
            f"   Цена: {product.price_rub} руб."
            if product.price_rub
            else "   Цена: не указана"
        )
        print(
            f"   Производитель: {product.manufacturer}"
            if product.manufacturer
            else "   Производитель: не указан"
        )

    # Сохраняем результат в JSON файл
    if products:
        with open("board_games.json", "w", encoding="utf-8") as f:
            json.dump(
                [product.model_dump() for product in products],
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info("Данные сохранены в board_games.json")


if __name__ == "__main__":
    asyncio.run(main())
