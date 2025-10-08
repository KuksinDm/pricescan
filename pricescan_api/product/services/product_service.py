import logging
from typing import Dict, List

from django.utils.text import slugify
from unidecode import unidecode

from ..constants import DEFAULT_CATEGORY, DEFAULT_PUBLISHER
from ..models import Product
from .game_parsers import GameDataParser

logger = logging.getLogger("parser_results")


class ProductService:
    def create_or_update_product_from_data(
        self, data: Dict, shop=None
    ) -> Dict:
        """Создание или обновление продукта из данных парсера"""
        try:
            title = data.get("title", "").strip()
            if not title:
                raise ValueError("Product title is required")

            # Создаем или получаем продукт
            product, created = Product.objects.get_or_create(
                title=title, defaults={"slug": slugify(unidecode(title))}
            )

            if created:
                # Парсим данные для нового продукта
                self._setup_product_relations(product, data)
                logger.info(f"Created new product: {product.title}")
            else:
                # Обновляем существующий продукт
                self._update_game_characteristics(product, data, [])
                logger.info(f"Updated existing product: {product.title}")

            return {"product": product, "created": created}

        except Exception as e:
            logger.error(f"Error creating product from data: {e}")
            raise

    def _setup_product_relations(self, product: Product, product_data: Dict):
        manufacturers = product_data.get("manufacturers", [])
        publishers = GameDataParser.parse_publishers(
            ", ".join(manufacturers) if manufacturers else DEFAULT_PUBLISHER
        )
        product.publishers.set(publishers)

        categories_data = product_data.get("categories", [])
        categories = GameDataParser.parse_categories(
            ", ".join(categories_data) if categories_data else DEFAULT_CATEGORY
        )
        product.categories.set(categories)

        players_range = GameDataParser.parse_players_range(product_data.get("players"))
        if players_range:
            product.min_players, product.max_players = players_range

        product.min_age = GameDataParser.parse_age(product_data.get("age"))
        product.playtime_min = GameDataParser.parse_playtime(
            product_data.get("play_time")
        )
        product.save()

    def _update_game_characteristics(
        self, product: Product, parser_result: Dict, updated_fields: List[str]
    ):
        if parser_result.get("players"):
            players_range = GameDataParser.parse_players_range(parser_result["players"])
            if players_range:
                product.min_players, product.max_players = players_range
                updated_fields.extend(["min_players", "max_players"])

        if parser_result.get("age"):
            age = GameDataParser.parse_age(parser_result["age"])
            if age:
                product.min_age = age
                updated_fields.append("min_age")

        if parser_result.get("play_time"):
            playtime = GameDataParser.parse_playtime(parser_result["play_time"])
            if playtime:
                product.playtime_min = playtime
                updated_fields.append("playtime_min")
