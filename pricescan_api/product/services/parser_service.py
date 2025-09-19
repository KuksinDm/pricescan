import logging
from decimal import Decimal

import requests
from django.utils.text import slugify

from ..models import Author, Category, Offer, PriceHistory, Product, Publisher, Shop

logger = logging.getLogger("parser_results")


import logging

logger = logging.getLogger("parser_results")


class HobbyGamesParserService:
    """Сервис для парсинга товаров с HobbyGames.ru"""

    def parse_product(self, product_id: int, shop_id: int, url: str = None):
        """Основная логика парсинга - СИНХРОННАЯ"""
        parse_url = self._get_parse_url(product_id, shop_id, url)
        if not parse_url:
            return {"ok": False, "error": "Offer not found"}

        result = self._fetch_product_data(parse_url)
        if not result or result.get("error"):
            return {"ok": False, "error": result.get("error", "No product data")}

        self._save_offer_and_history(product_id, shop_id, result, parse_url)
        self._update_product_metadata(product_id, result)

        return {
            "ok": True,
            "updated": True,
            "price": result.get("price"),
            "author": result.get("author"),
            "publisher": result.get("publisher"),
        }

    def _get_parse_url(self, product_id: int, shop_id: int, url: str = None):
        """Получить URL для парсинга - СИНХРОННАЯ"""
        if url:
            return url
        offer = Offer.objects.filter(product_id=product_id, shop_id=shop_id).first()
        return offer.url if offer else None

    def _fetch_product_data(self, parse_url: str):
        """Получить данные товара через API парсера - СИНХРОННАЯ"""
        try:
            response = requests.post(
                "http://pricescan_parser:8000/parse/product",
                json={"url": parse_url},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Parser service unavailable: {e}")
            return {"error": "Parser service unavailable"}

    def _save_offer_and_history(
        self, product_id: int, shop_id: int, result: dict, parse_url: str
    ):
        """Сохранить оффер и историю цен"""
        offer, created = Offer.objects.update_or_create(
            product_id=product_id,
            shop_id=shop_id,
            defaults={
                "price": Decimal(str(result["price"])) if result.get("price") else None,
                "currency": result.get("currency", "RUB"),
                "is_available": result.get("is_available", False),
                "url": result.get("url", parse_url),
            },
        )

        if result.get("price"):
            PriceHistory.objects.create(
                offer=offer,
                price=Decimal(str(result["price"])),
                currency=result.get("currency", "RUB"),
            )

    def _update_product_metadata(self, product_id: int, result: dict):
        """Обновить метаданные продукта"""
        # Создаем связанные объекты
        author_obj = self._get_or_create_author(result.get("author"))
        publisher_obj = self._get_or_create_publisher(result.get("publisher"))
        category_obj = self._get_or_create_category(result.get("category"))

        # Обновляем продукт
        try:
            product = Product.objects.get(id=product_id)
            updated = self._update_product_fields(
                product, result, author_obj, publisher_obj, category_obj
            )

            if updated:
                product.save()
                logger.info(f"Updated product {product_id} metadata")

        except Product.DoesNotExist:
            logger.warning(f"Product {product_id} not found for metadata update")

    def _get_or_create_author(self, name):
        """Создать или получить автора"""
        if not name:
            return None
        author_obj, _ = Author.objects.get_or_create(
            name=name, defaults={"slug": slugify(name)}
        )
        return author_obj

    def _get_or_create_publisher(self, name):
        """Создать или получить издателя"""
        if not name:
            return None
        publisher_obj, _ = Publisher.objects.get_or_create(
            name=name, defaults={"slug": slugify(name)}
        )
        return publisher_obj

    def _get_or_create_category(self, name):
        """Создать или получить категорию"""
        if not name:
            return None
        category_obj, _ = Category.objects.get_or_create(
            name=name, defaults={"slug": slugify(name)}
        )
        return category_obj

    def _update_product_fields(
        self, product, result, author_obj, publisher_obj, category_obj
    ):
        """Обновить поля продукта"""
        updated = False

        # Обновляем связи
        if author_obj and not product.author:
            product.author = author_obj
            updated = True
        if publisher_obj and not product.publisher:
            product.publisher = publisher_obj
            updated = True
        if category_obj and not product.category:
            product.category = category_obj
            updated = True

        # Обновляем метаданные
        fields_to_update = [
            ("description", "description"),
            ("image_url", "image_url"),
            ("players_min", "min_players"),
            ("players_max", "max_players"),
            ("playtime_min", "playtime_min"),
            ("age_min", "min_age"),
        ]

        for result_field, product_field in fields_to_update:
            if result.get(result_field) and not getattr(product, product_field):
                setattr(product, product_field, result[result_field])
                updated = True

        return updated

    def discover_products(self, query: str = "настольные игры", limit: int = 50):
        """Первичный сбор товаров с HobbyGames.ru"""
        try:
            # Парсим каталог через API парсера
            response = requests.post(
            "http://pricescan_parser:8000/parse/search",
            json={"query": query, "limit": limit},
            timeout=120
            )
            response.raise_for_status()
            search_result = response.json()

            products_created = 0
            offers_created = 0

            # Получаем магазин HobbyGames
            hobbygames_shop = Shop.objects.filter(
                domain__contains="hobbygames.ru", is_active=True
            ).first()

            if not hobbygames_shop:
                return {"ok": False, "error": "HobbyGames shop not found"}

            for product_data in search_result.get("products", []):
                try:
                    result = self._create_product_from_data(
                        product_data, hobbygames_shop
                    )
                    products_created += result.get("products_created", 0)
                    offers_created += result.get("offers_created", 0)

                except Exception as e:
                    logger.error(
                        f"Error creating product {product_data.get('title')}: {e}"
                    )

            return {
                "ok": True,
                "products_created": products_created,
                "offers_created": offers_created,
            }

        except Exception as e:
            logger.error(f"Discovery error: {e}")
            return {"ok": False, "error": str(e)}

    def _create_product_from_data(self, product_data: dict, shop):
        """Создать продукт и оффер из данных парсера"""
        # Создаем связанные объекты
        author_obj = self._get_or_create_author(product_data.get("author"))
        publisher_obj = self._get_or_create_publisher(product_data.get("publisher"))
        category_obj = self._get_or_create_category(product_data.get("category"))

        # Создаем продукт
        product, created = Product.objects.get_or_create(
            title=product_data["title"],
            defaults={
                "author": author_obj,
                "publisher": publisher_obj,
                "category": category_obj,
                "slug": slugify(product_data["title"]),
                "description": product_data.get("description", ""),
                "image_url": product_data.get("image_url", ""),
                "min_players": product_data.get("players_min"),
                "max_players": product_data.get("players_max"),
                "playtime_min": product_data.get("playtime_min"),
                "min_age": product_data.get("age_min"),
            },
        )

        products_created = 1 if created else 0

        # Создаем оффер
        offers_created = 0
        if product_data.get("price"):
            offer, offer_created = Offer.objects.get_or_create(
                product=product,
                shop=shop,
                defaults={
                    "price": Decimal(str(product_data["price"])),
                    "currency": product_data.get("currency", "RUB"),
                    "is_available": product_data.get("is_available", True),
                    "url": product_data["url"],
                },
            )
            offers_created = 1 if offer_created else 0

        return {"products_created": products_created, "offers_created": offers_created}
