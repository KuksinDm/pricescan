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

        # Обновляем игровые характеристики
        self._update_game_characteristics(product, parser_result, updated_fields)

        if updated_fields:
            product.save(update_fields=updated_fields)

        return updated_fields

    def create_or_update_product_from_data(self, product_data: Dict, shop) -> Dict:
        """Создание или обновление товара из данных парсера"""
        logger.info("=== PRODUCT SERVICE: Creating/updating product ===")
        logger.info(f"Product data: {product_data}")

        with transaction.atomic():
            title = product_data.get("title", "").strip()
            if not title:
                logger.error("Product title is missing")
                raise ValueError("Product title is required")

            logger.info(f"Processing product: {title}")

            # Поиск по названию
            product = Product.objects.filter(title=title).first()
            logger.info(f"Found product by title: {product}")

            created = False
            if not product:
                logger.info("Creating new product")
                # Создаем новый товар
                product = Product.objects.create(title=title)

                # Создаем и добавляем связи ManyToMany
                self._setup_product_relations(product, product_data)

                logger.info(f"Product created: {product}")
                created = True
            else:
                # Обновляем связи для существующего продукта
                self._update_product_relations(product, product_data)

            logger.info(f"Final result: created={created}, product_id={product.id}")
            return {
                "created": created,
                "product_id": product.id,
                "product": product,
            }

    def _setup_product_relations(self, product: Product, product_data: Dict):
        """Настройка связей для нового продукта"""
        # Авторы
        authors = self._parse_authors(product_data.get("manufacturer", "Неизвестно"))
        product.authors.set(authors)

        # Издатели
        publishers = self._parse_publishers(
            product_data.get("manufacturer", "Неизвестно")
        )
        product.publishers.set(publishers)

        # Категории
        categories = self._parse_categories("Настольные игры")
        product.categories.set(categories)

        # Игровые характеристики
        players_range = self._parse_players_range(product_data.get("players"))
        if players_range:
            product.min_players, product.max_players = players_range

        product.min_age = self._parse_age(product_data.get("age"))
        product.playtime_min = self._parse_playtime(product_data.get("play_time"))

        product.save()

    def _update_product_relations(self, product: Product, product_data: Dict):
        """Обновление связей для существующего продукта"""
        # Добавляем новых авторов/издателей/категории если нужно
        # (пока просто логируем)
        logger.info(f"Updating relations for product {product.id}")

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

    def _parse_authors(self, author_str: str) -> List[Author]:
        """Парсинг авторов"""
        if not author_str:
            author_str = "Неизвестно"

        # Разделяем по запятым если несколько авторов
        author_names = [name.strip() for name in author_str.split(",")]
        authors = []

        for name in author_names:
            if name:
                author, _ = Author.objects.get_or_create(
                    name=name, defaults={"slug": slugify(unidecode(name))}
                )
                authors.append(author)

        return authors if authors else [self._get_or_create_author("Неизвестно")]

    def _parse_publishers(self, publisher_str: str) -> List[Publisher]:
        """Парсинг издателей"""
        if not publisher_str:
            publisher_str = "Неизвестно"

        # Разделяем по запятым если несколько издателей
        publisher_names = [name.strip() for name in publisher_str.split(",")]
        publishers = []

        for name in publisher_names:
            if name:
                publisher, _ = Publisher.objects.get_or_create(
                    name=name, defaults={"slug": slugify(unidecode(name))}
                )
                publishers.append(publisher)

        return (
            publishers if publishers else [self._get_or_create_publisher("Неизвестно")]
        )

    def _parse_categories(self, category_str: str) -> List[Category]:
        """Парсинг категорий"""
        if not category_str:
            category_str = "Неизвестно"

        # Разделяем по запятым если несколько категорий
        category_names = [name.strip() for name in category_str.split(",")]
        categories = []

        for name in category_names:
            if name:
                category, _ = Category.objects.get_or_create(
                    name=name, defaults={"slug": slugify(unidecode(name))}
                )
                categories.append(category)

        return (
            categories if categories else [self._get_or_create_category("Неизвестно")]
        )

    def _get_or_create_author(self, name: str) -> Author:
        """Получение или создание автора"""
        safe_name = name or "Неизвестно"
        author, created = Author.objects.get_or_create(
            name=safe_name, defaults={"slug": slugify(unidecode(safe_name))}
        )
        return author

    def _get_or_create_publisher(self, name: str) -> Publisher:
        """Получение или создание издателя"""
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
