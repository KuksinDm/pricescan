import logging
from typing import Iterable

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from user.models import User, UserFavorite

from .models import Offer, PriceAlert, Shop
from .services.universal_parser_service import UniversalParserService

logger = logging.getLogger("parser_results")


@shared_task(queue="light")
def parse_product_universal(product_id: int, shop_id: int, url: str = None):
    try:
        service = UniversalParserService()
        result = service.parse_product(product_id, shop_id, url)

        if result["ok"]:
            logger.info(
                f"Updated product {product_id}: "
                f"{result.get('price')} {result.get('title', '')}"
            )

        return result
    except Exception as e:
        logger.error(f"Parse error for product {product_id}: {e}")
        return {"ok": False, "error": str(e)}


@shared_task(queue="light")
def bulk_parse_all_shops() -> dict:
    """Массовый парсинг всех товаров по всем магазинам (раз в 3 дня)"""
    try:
        total_parsed = 0
        results = {}

        # Получаем все активные магазины
        shops = Shop.objects.filter(is_active=True)

        for shop in shops:
            logger.info(
                f"Starting bulk parse for shop: {shop.name} ({shop.parser_type})"
            )

            # Получаем все офферы этого магазина
            offers = Offer.objects.filter(shop=shop)

            if offers.exists():
                # Обновляем существующие товары
                logger.info(
                    f"Updating {offers.count()} existing products for {shop.name}"
                )

                for offer in offers:
                    parse_product_universal.delay(offer.product.id, shop.id, offer.url)
                    total_parsed += 1

                results[shop.name] = {
                    "action": "update",
                    "queued": offers.count(),
                    "parser_type": shop.parser_type,
                }
            else:
                # Для новых магазинов запускаем поиск товаров
                discover_products_for_shop.delay(shop.id)
                results[shop.name] = {
                    "action": "discover",
                    "parser_type": shop.parser_type,
                }

        return {
            "ok": True,
            "total_queued": total_parsed,
            "shops_processed": len(shops),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Bulk parse error: {e}")
        return {"ok": False, "error": str(e)}


@shared_task(queue="light")
def monitor_favorite_products(user_id: int) -> int:
    """Мониторинг избранных товаров пользователя каждые 2 часа"""

    favorites = UserFavorite.objects.filter(user_id=user_id).select_related("product")
    count = 0

    for favorite in favorites:
        refresh_product.delay(favorite.product.id)
        count += 1

    logger.info(f"Queued monitoring for {count} favorite products of user {user_id}")
    return count


@shared_task(queue="light")
def monitor_all_user_favorites() -> int:
    """Мониторинг всех пользовательских избранных товаров"""

    users_with_favorites = User.objects.filter(favorites__isnull=False).distinct()
    count = 0

    for user in users_with_favorites:
        monitor_favorite_products.delay(user.id)
        count += 1

    logger.info(f"Queued favorite monitoring for {count} users")
    return count


def _dispatch_for_shop(product_id: int, shop: Shop):
    """Диспетчер парсеров по типу магазина - теперь универсальный"""
    # Получаем URL из существующего оффера
    offer = Offer.objects.filter(product_id=product_id, shop=shop).first()
    url = offer.url if offer else None

    # Все парсеры теперь используют универсальный сервис
    parse_product_universal.delay(product_id, shop.id, url)


@shared_task(queue="light")
def refresh_product(product_id: int) -> int:
    """Запланировать обновление по всем активным магазинам, где есть офферы продукта."""
    shops: Iterable[Shop] = Shop.objects.filter(
        is_active=True, offer__product_id=product_id
    ).distinct()
    count = 0

    for shop in shops:
        _dispatch_for_shop(product_id, shop)
        count += 1

    logger.info("Queued %s parse jobs for product=%s", count, product_id)

    # После обновления — проверяем алерты
    check_alerts_for_product.delay(product_id)
    return count


@shared_task(queue="light")
def refresh_all_prices() -> int:
    """Периодический запуск — пройтись по всем продуктам с офферами."""
    product_ids = Offer.objects.values_list("product_id", flat=True).distinct()
    total = 0

    for pid in product_ids:
        refresh_product.delay(pid)
        total += 1

    logger.info("Queued refresh for %s products", total)
    return total


@shared_task(queue="light")
def check_alerts_for_product(product_id: int) -> int:
    """Проверить и сработать пользовательские алерты по продукту."""
    # Текущая минимальная цена
    min_offer = (
        Offer.objects.filter(product_id=product_id, is_available=True)
        .order_by("price")
        .first()
    )

    if not min_offer:
        return 0

    alerts = PriceAlert.objects.filter(
        product_id=product_id, is_active=True, currency=min_offer.currency
    )
    triggered = alerts.filter(threshold_price__gte=min_offer.price)

    count = 0
    for alert in triggered:
        try:
            # Проверяем, что у пользователя есть telegram_id
            if not alert.user.telegram_id:
                logger.warning(
                    f"User {alert.user_id} has no telegram_id, skipping alert"
                )
                continue

            # URL на FastAPI бота
            bot_url = "http://bot_pricescan:8000/send_alert"
            payload = {
                "user_id": alert.user.telegram_id,  # ← Используем telegram_id вместо user_id
                "product_id": product_id,
                "price": float(min_offer.price),
                "url": min_offer.url,
                "alert_id": alert.id,
            }
            # Добавляем сервисный токен в заголовки
            headers = {
                "X-Service-Token": settings.BOT_SERVICE_TOKEN,
                "Content-Type": "application/json",
            }
            requests.post(bot_url, json=payload, headers=headers, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send alert to bot: {e}")
        logger.info(
            "ALERT TRIGGER user=%s product=%s price=%s url=%s",
            alert.user.telegram_id,  # ← И в логах тоже telegram_id
            product_id,
            min_offer.price,
            min_offer.url,
        )
        alert.last_triggered_at = timezone.now()
        alert.is_active = False  # авто-выключение после срабатывания
        alert.save(update_fields=["last_triggered_at", "is_active"])
        count += 1


@shared_task(queue="heavy")
def discover_products_for_shop(
    shop_id: int, query: str = "настольная игра", limit: int = 1000
) -> dict:
    """Обнаружение новых товаров для конкретного магазина"""
    try:
        service = UniversalParserService()
        result = service.discover_products(shop_id, query, limit)

        if result["ok"]:
            logger.info(
                f"Shop {shop_id}: found {result['products_found']} products, "
                f"created {result['products_created']} new products, "
                f"created {result['offers_created']} new offers"
            )

        return result

    except Exception as e:
        logger.error(f"Discover products for shop {shop_id} error: {e}")
        return {"ok": False, "error": str(e)}


@shared_task(queue="light")
def update_shop_products(shop_id: int) -> dict:
    """Обновление всех товаров конкретного магазина"""
    try:
        shop = Shop.objects.get(id=shop_id)
        offers = Offer.objects.filter(shop=shop, is_available=True)

        count = 0
        for offer in offers:
            parse_product_universal.delay(offer.product.id, shop.id, offer.url)
            count += 1

        logger.info(f"Queued {count} products for shop {shop.name}")
        return {"ok": True, "queued": count}

    except Exception as e:
        logger.error(f"Update shop products error: {e}")
        return {"ok": False, "error": str(e)}


@shared_task(queue="light")
def health_check_parsers() -> dict:
    """Проверка здоровья всех парсеров"""
    service = UniversalParserService()
    results = {}

    # Исправляем обращение к parser_endpoints
    for parser_type, endpoint in service.parser_service.parser_endpoints.items():
        try:
            response = requests.get(f"{endpoint}/health", timeout=10)
            results[parser_type] = {
                "status": "ok" if response.status_code == 200 else "error",
                "response_time": response.elapsed.total_seconds(),
                "status_code": response.status_code,
            }
        except Exception as e:
            results[parser_type] = {"status": "error", "error": str(e)}

    return {"ok": True, "parsers": results}
