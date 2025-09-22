"""
Сервис для работы с продуктами
Обеспечивает создание и обновление продуктов из данных парсеров
"""

import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple

from django.db import transaction

from ..models import (
    Author,
    Category,
    Offer,
    PriceAlert,
    PriceHistory,
    Product,
    Publisher,
    Shop,
)

logger = logging.getLogger(__name__)


class ProductService:
    """Сервис для работы с продуктами"""

    @classmethod
    def create_or_update_from_parser_data(
        cls, product_data: Dict, shop: Shop
    ) -> Tuple[Product, bool]:
        """
        Создание или обновление продукта из данных парсера

        Args:
            product_data: Данные продукта от парсера
            shop: Магазин

        Returns:
            Tuple[Product, bool]: (продукт, создан_ли_новый)
        """
        with transaction.atomic():
            # Извлекаем данные продукта
            title = product_data.get("title", "").strip()
            if not title:
                raise ValueError("Название продукта не может быть пустым")

            # Создаем или получаем автора
            author_name = product_data.get("manufacturer", "Неизвестный автор")
            author, _ = Author.objects.get_or_create(
                name=author_name, defaults={"name": author_name}
            )

            # Создаем или получаем категорию
            category_name = "Настольные игры"  # По умолчанию
            category, _ = Category.objects.get_or_create(
                name=category_name, defaults={"name": category_name}
            )

            # Создаем или получаем издателя (если есть)
            publisher = None
            if product_data.get("publisher"):
                publisher, _ = Publisher.objects.get_or_create(
                    name=product_data["publisher"],
                    defaults={"name": product_data["publisher"]},
                )

            # Парсим дополнительные данные
            players = product_data.get("players", "")
            min_players, max_players = cls._parse_players_range(players)

            play_time = product_data.get("play_time", "")
            playtime_min = cls._parse_playtime(play_time)

            age = product_data.get("age", "")
            min_age = cls._parse_age(age)

            # Создаем или обновляем продукт
            product, created = Product.objects.get_or_create(
                title=title,
                defaults={
                    "author": author,
                    "publisher": publisher,
                    "category": category,
                    "description": product_data.get("description", ""),
                    "image_url": product_data.get("image_url", ""),
                    "min_players": min_players,
                    "max_players": max_players,
                    "playtime_min": playtime_min,
                    "min_age": min_age,
                    "external_id": product_data.get("external_id", ""),
                    "brand": product_data.get("manufacturer", ""),
                },
            )

            # Создаем или обновляем предложение
            price = product_data.get("price_rub")
            if price and price > 0:
                offer, offer_created = Offer.objects.get_or_create(
                    product=product,
                    shop=shop,
                    defaults={
                        "price": Decimal(str(price)),
                        "currency": "RUB",
                        "is_available": True,
                        "url": product_data.get("url", ""),
                    },
                )

                if not offer_created:
                    # Обновляем существующее предложение
                    old_price = offer.price
                    offer.price = Decimal(str(price))
                    offer.is_available = True
                    offer.url = product_data.get("url", "")
                    offer.save()

                    # Сохраняем историю цены, если она изменилась
                    if old_price != offer.price:
                        PriceHistory.objects.create(
                            offer=offer, price=old_price, currency="RUB"
                        )

            return product, created

    @classmethod
    def update_product_prices(cls, product: Product) -> int:
        """
        Обновление цен продукта во всех магазинах

        Args:
            product: Продукт для обновления

        Returns:
            int: Количество обновленных магазинов
        """
        updated_count = 0
        shops = Shop.objects.filter(is_active=True)

        for shop in shops:
            try:
                # Здесь можно реализовать поиск конкретного продукта
                # через соответствующий парсер
                logger.info(f"Обновление цены {product.title} в магазине {shop.name}")
                updated_count += 1

            except Exception as e:
                logger.error(f"Ошибка обновления цены в магазине {shop.name}: {e}")
                continue

        return updated_count

    @classmethod
    def check_price_alerts(cls, product: Product) -> int:
        """
        Проверка алертов для продукта

        Args:
            product: Продукт для проверки

        Returns:
            int: Количество сработавших алертов
        """
        active_alerts = PriceAlert.objects.filter(
            product=product, is_active=True
        ).select_related("user", "shop")

        if not active_alerts.exists():
            return 0

        triggered_count = 0

        for alert in active_alerts:
            try:
                # Получаем текущие предложения по продукту
                offers = Offer.objects.filter(product=product, is_available=True)

                if alert.shop:
                    offers = offers.filter(shop=alert.shop)

                # Проверяем, есть ли предложения ниже порога
                cheap_offers = offers.filter(price__lte=alert.threshold_price)

                if cheap_offers.exists():
                    # Алерт сработал
                    cls._trigger_price_alert(alert, cheap_offers.first())
                    triggered_count += 1

            except Exception as e:
                logger.error(f"Ошибка проверки алерта {alert.id}: {e}")
                continue

        return triggered_count

    @classmethod
    def _parse_players_range(
        cls, players_str: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """Парсинг диапазона игроков '1-2' -> (1, 2)"""
        if not players_str:
            return None, None

        try:
            if "-" in players_str:
                parts = players_str.split("-")
                if len(parts) == 2:
                    return int(parts[0].strip()), int(parts[1].strip())
            elif players_str.isdigit():
                val = int(players_str)
                return val, val
        except (ValueError, IndexError):
            pass

        return None, None

    @classmethod
    def _parse_playtime(cls, playtime_str: str) -> Optional[int]:
        """Парсинг времени игры '60-120' -> 60 (минимальное время)"""
        if not playtime_str:
            return None

        try:
            if "-" in playtime_str:
                parts = playtime_str.split("-")
                if len(parts) == 2:
                    return int(parts[0].strip())
            elif playtime_str.isdigit():
                return int(playtime_str)
        except (ValueError, IndexError):
            pass

        return None

    @classmethod
    def _parse_age(cls, age_str: str) -> Optional[int]:
        """Парсинг возраста '14+' -> 14"""
        if not age_str:
            return None

        try:
            # Убираем '+' и парсим число
            age_str = age_str.replace("+", "").strip()
            if age_str.isdigit():
                return int(age_str)
        except ValueError:
            pass

        return None

    @classmethod
    def _trigger_price_alert(cls, alert: PriceAlert, offer: Offer):
        """Срабатывание алерта о цене"""
        try:
            from django.utils import timezone

            # Обновляем время последнего срабатывания
            alert.last_triggered_at = timezone.now()
            alert.save(update_fields=["last_triggered_at"])

            # Здесь можно добавить отправку уведомления пользователю
            # через Telegram бот или email

            logger.info(
                f"Алерт сработал для пользователя {alert.user.id}: {offer.product.title} - {offer.price} руб. в {offer.shop.name}"
            )

        except Exception as e:
            logger.error(f"Ошибка срабатывания алерта {alert.id}: {e}")
