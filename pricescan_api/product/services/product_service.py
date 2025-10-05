import logging
import re
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.utils.text import slugify
from unidecode import unidecode

from ..models import Category, Product, Publisher

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
        logger.info(f"Product data keys: {list(product_data.keys())}")
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
        logger.info("=== SETTING UP PRODUCT RELATIONS ===")
        logger.info(f"Product data: {product_data}")

        # Производители (издатели)
        manufacturers = product_data.get("manufacturers", [])
        logger.info(f"Manufacturers from data: {manufacturers}")

        if manufacturers:
            publishers = self._parse_publishers(", ".join(manufacturers))
            logger.info(f"Parsed publishers: {[p.name for p in publishers]}")
        else:
            publishers = self._parse_publishers("Неизвестно")
            logger.info(f"Default publishers: {[p.name for p in publishers]}")
        product.publishers.set(publishers)

        # Категории
        categories_data = product_data.get("categories", [])
        logger.info(f"Categories from data: {categories_data}")

        if categories_data:
            categories = self._parse_categories(", ".join(categories_data))
            logger.info(f"Parsed categories: {[c.name for c in categories]}")
        else:
            categories = self._parse_categories("Настольные игры")
            logger.info(f"Default categories: {[c.name for c in categories]}")
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

    def _get_or_create_publisher(self, name: str) -> Publisher:
        """Получение или создание издателя"""
        safe_name = name or "Неизвестно"
        publisher, created = Publisher.objects.get_or_create(
            name=safe_name, defaults={"slug": slugify(unidecode(safe_name))}
        )
        return publisher

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

    # def _get_or_create_publisher(self, name: str) -> Publisher:
    #     """Получение или создание издателя"""
    #     safe_name = name or "Неизвестно"
    #     publisher, created = Publisher.objects.get_or_create(
    #         name=safe_name, defaults={"slug": slugify(unidecode(safe_name))}
    #     )
    #     return publisher

    def _get_or_create_category(self, name: str) -> Category:
        """Получение или создание категории"""
        safe_name = name or "Неизвестно"
        category, created = Category.objects.get_or_create(
            name=name, defaults={"slug": slugify(unidecode(safe_name))}
        )
        return category

    def _parse_players_range(self, players_str: str) -> Optional[Tuple[int, int]]:
        if not players_str:
            return None
        s = str(players_str).strip().lower().replace("–", "-").replace("—", "-")

        m = re.search(r"от\s*(\d+)\s*до\s*(\d+)", s) or re.search(
            r"(\d+)\s*-\s*(\d+)", s
        )
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            return (min(a, b), max(a, b))

        m = re.search(r"(\d+)\s*\+", s)
        if m:
            n = int(m.group(1))
            return (n, n)

        m = re.search(r"\b(\d+)\b", s)
        if m:
            n = int(m.group(1))
            return (n, n)

        return None

    # def _parse_players_range(self, players_str: str) -> Optional[Tuple[int, int]]:
    #     """Парсинг диапазона игроков"""
    #     if not players_str:
    #         return None

    #     try:
    #         if "-" in players_str:
    #             parts = players_str.split("-")
    #             if len(parts) == 2:
    #                 min_players = int(parts[0].strip())
    #                 max_players = int(parts[1].strip())
    #                 return (min_players, max_players)
    #         else:
    #             players = int(players_str.strip())
    #             return (players, players)
    #     except (ValueError, IndexError) as e:
    #         logger.debug(f"Failed to parse players range '{players_str}': {e}")

    #     return None

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
        """Парсинг времени игры → минимальные минуты"""
        if not playtime_str:
            return None

        s = playtime_str.lower().replace("\xa0", " ").strip()

        # 1) "1 ч 30 мин"
        m = re.search(r"(\d+)\s*ч(?:ас(?:а|ов)?)?\s*(\d+)\s*мин", s)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))

        # 2) "1–2 часа" / "1-2 ч" / "1 ч"
        m = re.search(r"(\d+)\s*(?:[–-]\s*\d+\s*)?(?:ч|час(?:а|ов)?)", s)
        if m:
            return int(m.group(1)) * 60

        # 3) "от 30 мин", "30–60 мин", "30 мин", "от 20 до 90 минут"
        m = re.search(r"(?:от\s*)?(\d+)\s*(?:до\s*\d+\s*)?мин", s) or re.search(
            r"(?:от\s*)?(\d+)\s*(?:[–-]\s*\d+)?\s*мин", s
        )
        if m:
            return int(m.group(1))

        # 4) "30–60" / "90-120" (без единиц)
        m = re.search(r"(\d+)\s*[–-]\s*\d+", s)
        if m:
            return int(m.group(1))

        # 5) "60+" (минут/часы)
        m = re.search(r"(\d+)\s*\+", s)
        if m:
            n = int(m.group(1))
            return n * 60 if re.search(r"(?:^|\s)(?:ч|час)", s) else n

        # 6) Фолбэк: первое число; если рядом "ч" — считаем часами
        m = re.search(r"(\d+)", s)
        if m:
            n = int(m.group(1))
            return n * 60 if re.search(r"(?:^|\s)(?:ч|час)", s) else n
        return None
