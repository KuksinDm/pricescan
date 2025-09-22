import asyncio
import logging
from decimal import Decimal
from typing import Dict, Optional

import httpx
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import (
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


# ========== ОСНОВНЫЕ ЗАДАЧИ ПАРСИНГА ==========


@shared_task(queue="heavy")
def parse_playwright(shop_id: int, category_url: str = None, max_products: int = 50):
    """
    Парсинг через Playwright (для SPA сайтов)
    Использует pricescan_playwright сервис
    """
    try:
        shop = Shop.objects.get(id=shop_id, parser_type="playwright")
        logger.info(f"Запуск Playwright парсинга для магазина {shop.name}")

        # Вызываем Playwright парсер через HTTP API
        async def _parse():
            async with httpx.AsyncClient(timeout=300.0) as client:
                if category_url:
                    # Парсинг конкретной категории
                    response = await client.post(
                        "http://pricescan_playwright:8000/parse/search",
                        json={
                            "query": "настольные игры",
                            "limit": max_products,
                            "max_pages": 3,
                            "max_products": max_products,
                        },
                    )
                else:
                    # Общий поиск
                    response = await client.post(
                        "http://pricescan_playwright:8000/parse/search",
                        json={
                            "query": "настольные игры",
                            "limit": max_products,
                            "max_pages": 2,
                            "max_products": max_products,
                        },
                    )

                response.raise_for_status()
                return response.json()

        result = asyncio.run(_parse())
        products_data = result.get("products", [])

        # Обрабатываем результаты
        created_count = 0
        updated_count = 0

        for product_data in products_data:
            try:
                product, created = _create_or_update_product_from_parser_data(
                    product_data, shop, "playwright"
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                logger.error(
                    f"Ошибка обработки продукта {product_data.get('title', 'Unknown')}: {e}"
                )
                continue

        logger.info(
            f"Playwright парсинг завершен. Создано: {created_count}, Обновлено: {updated_count}"
        )
        return {"created": created_count, "updated": updated_count}

    except Exception as e:
        logger.error(f"Ошибка Playwright парсинга: {e}")
        raise


@shared_task(queue="light")
def parse_bs4(shop_id: int, category_url: str = None, max_products: int = 50):
    """
    Парсинг через BeautifulSoup (для простых HTML сайтов)
    Использует pricescan_parser сервис
    """
    try:
        shop = Shop.objects.get(id=shop_id, parser_type="beautifulsoup")
        logger.info(f"Запуск BeautifulSoup парсинга для магазина {shop.name}")

        # Вызываем BeautifulSoup парсер через HTTP API
        async def _parse():
            async with httpx.AsyncClient(timeout=300.0) as client:
                if category_url:
                    response = await client.post(
                        "http://pricescan_parser:8000/parse/search",
                        json={
                            "query": "настольные игры",
                            "limit": max_products,
                            "shop": "hobbygames",
                        },
                    )
                else:
                    response = await client.post(
                        "http://pricescan_parser:8000/parse/search",
                        json={
                            "query": "настольные игры",
                            "limit": max_products,
                            "shop": "hobbygames",
                        },
                    )

                response.raise_for_status()
                return response.json()

        result = asyncio.run(_parse())
        products_data = result.get("products", [])

        # Обрабатываем результаты
        created_count = 0
        updated_count = 0

        for product_data in products_data:
            try:
                product, created = _create_or_update_product_from_parser_data(
                    product_data, shop, "beautifulsoup"
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                logger.error(
                    f"Ошибка обработки продукта {product_data.get('title', 'Unknown')}: {e}"
                )
                continue

        logger.info(
            f"BeautifulSoup парсинг завершен. Создано: {created_count}, Обновлено: {updated_count}"
        )
        return {"created": created_count, "updated": updated_count}

    except Exception as e:
        logger.error(f"Ошибка BeautifulSoup парсинга: {e}")
        raise


@shared_task(queue="light")
def parse_api_json(
    shop_id: int, query: str = "настольные игры", max_products: int = 50
):
    """
    Парсинг через JSON API (для открытых API)
    Использует pricescan_parser сервис
    """
    try:
        shop = Shop.objects.get(id=shop_id, parser_type="api_json")
        logger.info(f"Запуск API JSON парсинга для магазина {shop.name}")

        # Вызываем API JSON парсер через HTTP API
        async def _parse():
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "http://pricescan_parser:8000/parse/search",
                    json={"query": query, "limit": max_products, "shop": "wildberries"},
                )
                response.raise_for_status()
                return response.json()

        result = asyncio.run(_parse())
        products_data = result.get("products", [])

        # Обрабатываем результаты
        created_count = 0
        updated_count = 0

        for product_data in products_data:
            try:
                product, created = _create_or_update_product_from_parser_data(
                    product_data, shop, "api_json"
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                logger.error(
                    f"Ошибка обработки продукта {product_data.get('title', 'Unknown')}: {e}"
                )
                continue

        logger.info(
            f"API JSON парсинг завершен. Создано: {created_count}, Обновлено: {updated_count}"
        )
        return {"created": created_count, "updated": updated_count}

    except Exception as e:
        logger.error(f"Ошибка API JSON парсинга: {e}")
        raise


# ========== ЗАДАЧИ ОБНОВЛЕНИЯ ЦЕН ==========


@shared_task(queue="light")
def refresh_product(product_id: int):
    """
    Обновление цен конкретного продукта во всех магазинах
    """
    try:
        product = Product.objects.get(id=product_id)
        logger.info(f"Обновление цен для продукта: {product.title}")

        updated_count = 0

        # Получаем все активные магазины
        shops = Shop.objects.filter(is_active=True)

        for shop in shops:
            try:
                if shop.parser_type == "playwright":
                    # Обновляем через Playwright
                    _update_product_price_playwright(product, shop)
                elif shop.parser_type == "beautifulsoup":
                    # Обновляем через BeautifulSoup
                    _update_product_price_bs4(product, shop)
                elif shop.parser_type == "api_json":
                    # Обновляем через API JSON
                    _update_product_price_api(product, shop)

                updated_count += 1

            except Exception as e:
                logger.error(f"Ошибка обновления цены в магазине {shop.name}: {e}")
                continue

        logger.info(f"Обновление цен завершено. Обновлено магазинов: {updated_count}")
        return {"updated_shops": updated_count}

    except Product.DoesNotExist:
        logger.error(f"Продукт с ID {product_id} не найден")
        return {"error": "Product not found"}
    except Exception as e:
        logger.error(f"Ошибка обновления продукта {product_id}: {e}")
        raise


@shared_task(queue="light")
def refresh_all_prices():
    """
    Массовое обновление цен всех продуктов (запускается по расписанию)
    """
    try:
        logger.info("Запуск массового обновления цен")

        # Получаем все активные магазины
        shops = Shop.objects.filter(is_active=True)

        total_updated = 0

        for shop in shops:
            try:
                if shop.parser_type == "playwright":
                    result = parse_playwright.delay(shop.id, max_products=100)
                elif shop.parser_type == "beautifulsoup":
                    result = parse_bs4.delay(shop.id, max_products=100)
                elif shop.parser_type == "api_json":
                    result = parse_api_json.delay(shop.id, max_products=100)
                else:
                    continue

                total_updated += 1

            except Exception as e:
                logger.error(f"Ошибка запуска парсинга для магазина {shop.name}: {e}")
                continue

        logger.info(f"Запущено обновлений для {total_updated} магазинов")
        return {"shops_updated": total_updated}

    except Exception as e:
        logger.error(f"Ошибка массового обновления цен: {e}")
        raise


# ========== ЗАДАЧИ МОНИТОРИНГА АЛЕРТОВ ==========


@shared_task(queue="light")
def check_alerts_for_product(product_id: int):
    """
    Проверка алертов для конкретного продукта
    """
    try:
        product = Product.objects.get(id=product_id)
        active_alerts = PriceAlert.objects.filter(
            product=product, is_active=True
        ).select_related("user", "shop")

        if not active_alerts.exists():
            return {"checked": 0, "triggered": 0}

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
                    _trigger_price_alert(alert, cheap_offers.first())
                    triggered_count += 1

            except Exception as e:
                logger.error(f"Ошибка проверки алерта {alert.id}: {e}")
                continue

        logger.info(
            f"Проверка алертов для продукта {product.title}: {triggered_count} сработало"
        )
        return {"checked": active_alerts.count(), "triggered": triggered_count}

    except Product.DoesNotExist:
        logger.error(f"Продукт с ID {product_id} не найден")
        return {"error": "Product not found"}
    except Exception as e:
        logger.error(f"Ошибка проверки алертов для продукта {product_id}: {e}")
        raise


@shared_task(queue="light")
def monitor_all_user_favorites():
    """
    Мониторинг всех пользовательских избранных (запускается по расписанию)
    """
    try:
        logger.info("Запуск мониторинга пользовательских избранных")

        # Получаем все активные алерты
        active_alerts = PriceAlert.objects.filter(is_active=True).select_related(
            "product", "user", "shop"
        )

        triggered_count = 0

        for alert in active_alerts:
            try:
                # Получаем текущие предложения по продукту
                offers = Offer.objects.filter(product=alert.product, is_available=True)

                if alert.shop:
                    offers = offers.filter(shop=alert.shop)

                # Проверяем, есть ли предложения ниже порога
                cheap_offers = offers.filter(price__lte=alert.threshold_price)

                if cheap_offers.exists():
                    # Алерт сработал
                    _trigger_price_alert(alert, cheap_offers.first())
                    triggered_count += 1

            except Exception as e:
                logger.error(f"Ошибка проверки алерта {alert.id}: {e}")
                continue

        logger.info(f"Мониторинг завершен. Сработало алертов: {triggered_count}")
        return {"checked": active_alerts.count(), "triggered": triggered_count}

    except Exception as e:
        logger.error(f"Ошибка мониторинга алертов: {e}")
        raise


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========


def _create_or_update_product_from_parser_data(
    product_data: Dict, shop: Shop, parser_type: str
) -> tuple[Product, bool]:
    """
    Создание или обновление продукта из данных парсера
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
        min_players, max_players = _parse_players_range(players)

        play_time = product_data.get("play_time", "")
        playtime_min = _parse_playtime(play_time)

        age = product_data.get("age", "")
        min_age = _parse_age(age)

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


def _parse_players_range(players_str: str) -> tuple[Optional[int], Optional[int]]:
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


def _parse_playtime(playtime_str: str) -> Optional[int]:
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


def _parse_age(age_str: str) -> Optional[int]:
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


def _update_product_price_playwright(product: Product, shop: Shop):
    """Обновление цены через Playwright"""
    # Здесь можно реализовать поиск конкретного продукта через Playwright API
    pass


def _update_product_price_bs4(product: Product, shop: Shop):
    """Обновление цены через BeautifulSoup"""
    # Здесь можно реализовать поиск конкретного продукта через BS4 API
    pass


def _update_product_price_api(product: Product, shop: Shop):
    """Обновление цены через API JSON"""
    # Здесь можно реализовать поиск конкретного продукта через API JSON
    pass


def _trigger_price_alert(alert: PriceAlert, offer: Offer):
    """Срабатывание алерта о цене"""
    try:
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


# ========== ЗАДАЧИ ДЛЯ СТАРЫХ НАЗВАНИЙ (совместимость) ==========


@shared_task(queue="light")
def bulk_parse_hobbygames():
    """Совместимость со старым названием задачи"""
    try:
        shop = Shop.objects.filter(parser_type="beautifulsoup", is_active=True).first()
        if shop:
            return parse_bs4.delay(shop.id, max_products=100)
        return {"error": "No active BeautifulSoup shop found"}
    except Exception as e:
        logger.error(f"Ошибка bulk_parse_hobbygames: {e}")
        raise
