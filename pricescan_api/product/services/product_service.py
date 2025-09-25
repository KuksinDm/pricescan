# pricescan_api/product/services/product_service.py
import logging
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.utils.text import slugify
from unidecode import unidecode

from ..models import Author, Category, Product, Publisher

logger = logging.getLogger("parser_results")


class ProductService:
    """Сервис для работы с товарами"""

    def update_product_info(self, product: Product, parser_result: Dict) -> List[str]:
        """Обновление информации о товаре"""
        updated_fields = []

        if parser_result.get("title") and not product.title:
            product.title = parser_result["title"]
            updated_fields.append("title")

        if parser_result.get("description") and not product.description:
            product.description = parser_result["description"]
            updated_fields.append("description")

        if parser_result.get("manufacturer") and not product.brand:
            product.brand = parser_result["manufacturer"]
            updated_fields.append("brand")

        # Обновляем игровые характеристики
        self._update_game_characteristics(product, parser_result, updated_fields)

        if updated_fields:
            product.save(update_fields=updated_fields)

        return updated_fields

    def create_or_update_product_from_data(self, product_data: Dict, shop) -> Dict:
        """Создание или обновление товара из данных парсера"""
        with transaction.atomic():
            title = product_data.get("title", "").strip()
            if not title:
                raise ValueError("Product title is required")

            # Поиск по названию или внешнему ID
            product = None
            if product_data.get("external_id"):
                product = Product.objects.filter(
                    external_id=product_data["external_id"]
                ).first()

            if not product:
                product = Product.objects.filter(title=title).first()

            created = False
            if not product:
                # Создаем новый товар
                author = self._get_or_create_author(product_data.get("Неизвестно"))
                category = self._get_or_create_category("Настольные игры")
                publisher = self._get_or_create_publisher(
                    product_data.get("manufacturer", "Неизвестно")
                )

                product, created = Product.objects.update_or_create(
                    title=title,
                    defaults={
                        "author": author,
                        "publisher": publisher,
                        "category": category,
                        "brand": product_data.get("brand"),
                        "description": product_data.get("description", ""),
                        "external_id": product_data.get("external_id"),
                        "min_age": self._parse_age(product_data.get("age")),
                        "playtime_min": self._parse_playtime(
                            product_data.get("play_time")
                        ),
                        "year": self._parse_year(product_data.get("year")),
                    },
                )

                # Устанавливаем диапазон игроков
                players_range = self._parse_players_range(product_data.get("players"))
                if players_range:
                    product.min_players, product.max_players = players_range
                    product.save(update_fields=["min_players", "max_players"])

                created = True

            return {
                "created": created,
                "product_id": product.id,
                "product": product,
            }

    def _update_game_characteristics(
        self, product: Product, parser_result: Dict, updated_fields: List[str]
    ):
        """Обновление игровых характеристик"""
        if parser_result.get("players"):
            players_range = self._parse_players_range(parser_result["players"])
            if players_range:
                product.min_players, product.max_players = players_range
                updated_fields.extend(["min_players", "max_players"])

        if parser_result.get("age"):
            age = self._parse_age(parser_result["age"])
            if age:
                product.min_age = age
                updated_fields.append("min_age")

        if parser_result.get("play_time"):
            playtime = self._parse_playtime(parser_result["play_time"])
            if playtime:
                product.playtime_min = playtime
                updated_fields.append("playtime_min")

    def _get_or_create_author(self, name: str) -> Author:
        """Получение или создание автора/производителя"""
        safe_name = name or "Неизвестно"  # Гарантируем не-None значение
        author, created = Author.objects.get_or_create(
            name=safe_name, defaults={"slug": slugify(unidecode(safe_name))}
        )
        return author

    def _get_or_create_publisher(self, name: str) -> Publisher:
        """Получение или создание издателя/производителя"""
        safe_name = name or "Неизвестно"
        publisher, created = Publisher.objects.get_or_create(
            name=safe_name, defaults={"slug": slugify(unidecode(safe_name))}
        )
        return publisher

    def _get_or_create_category(self, name: str) -> Category:
        """Получение или создание категории"""
        safe_name = name or "Неизвестно"
        category, created = Category.objects.get_or_create(
            name=name, defaults={"slug": slugify(unidecode(safe_name))}
        )
        return category

    def _parse_players_range(self, players_str: str) -> Optional[Tuple[int, int]]:
        """Парсинг диапазона игроков"""
        if not players_str:
            return None

        try:
            if "-" in players_str:
                parts = players_str.split("-")
                if len(parts) == 2:
                    min_players = int(parts[0].strip())
                    max_players = int(parts[1].strip())
                    return (min_players, max_players)
            else:
                players = int(players_str.strip())
                return (players, players)
        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse players range '{players_str}': {e}")

        return None

    def _parse_age(self, age_str: str) -> Optional[int]:
        """Парсинг возраста"""
        if not age_str:
            return None

        try:
            age_clean = age_str.replace("+", "").strip()
            return int(age_clean)
        except ValueError:
            return None

    def _parse_playtime(self, playtime_str: str) -> Optional[int]:
        """Парсинг времени игры"""
        if not playtime_str:
            return None

        try:
            if "-" in playtime_str:
                parts = playtime_str.split("-")
                return int(parts[0].strip())
            else:
                return int(playtime_str.strip())
        except (ValueError, IndexError):
            return None

    def _parse_year(self, year_data: any) -> Optional[int]:
        """Парсинг года выпуска"""
        if not year_data:
            return None

        if isinstance(year_data, int):
            return year_data

        if isinstance(year_data, str):
            import re

            years = re.findall(r"\b(19|20)\d{2}\b", year_data)
            if years:
                return int(max(years))

        return None
