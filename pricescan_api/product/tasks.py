import asyncio
import logging
from typing import Iterable

from celery import shared_task
from django.utils import timezone

from .models import (
    Offer,
    PriceAlert,
    Shop,
)
from .services.parser_service import HobbyGamesParserService

logger = logging.getLogger("parser_results")


@shared_task(queue="light")
def parse_hobbygames_product(product_id: int, shop_id: int, url: str = None):
    """Парсинг товара с HobbyGames через API парсера"""

    def _parse():
        try:
            service = HobbyGamesParserService()
            result = service.parse_product(product_id, shop_id, url)

            if result["ok"]:
                logger.info(f"Updated product {product_id}: {result.get('price')}")

            return result

        except Exception as e:
            logger.error(f"Parse error for product {product_id}: {e}")
            return {"ok": False, "error": str(e)}

    return _parse()


@shared_task(queue="light")
def bulk_parse_hobbygames() -> dict:
    """Массовый парсинг всех товаров HobbyGames (раз в 3 дня)"""

    def _bulk_parse():
        try:
            service = HobbyGamesParserService()

            # Проверяем, есть ли уже товары
            hobbygames_shop = Shop.objects.filter(
                domain__contains="hobbygames.ru", is_active=True
            ).first()

            if not hobbygames_shop:
                return {"ok": False, "error": "HobbyGames shop not found"}

            existing_offers = Offer.objects.filter(shop=hobbygames_shop)

            if existing_offers.exists():
                # Обновляем существующие
                logger.info(f"Updating {existing_offers.count()} existing products")
                for offer in existing_offers:
                    parse_hobbygames_product.delay(
                        offer.product.id, hobbygames_shop.id, offer.url
                    )
                return {
                    "ok": True,
                    "action": "update",
                    "queued": existing_offers.count(),
                }
            else:
                # Собираем новые товары
                logger.info("Discovering new products from HobbyGames.ru")
                result = service.discover_products()
                return result

        except Exception as e:
            logger.error(f"Bulk parse error: {e}")
            return {"ok": False, "error": str(e)}

    return _bulk_parse()


@shared_task(queue="light")
def monitor_favorite_products(user_id: int) -> int:
    """Мониторинг избранных товаров пользователя каждые 3 часа"""
    from user.models import UserFavorite

    favorites = UserFavorite.objects.filter(user_id=user_id).select_related("product")
    count = 0

    for favorite in favorites:
        refresh_product.delay(favorite.product.id)
        count += 1

    logger.info(f"Queued monitoring for {count} favorite products of user {user_id}")
    return count


@shared_task(queue="light")
def parse_api_json(product_id: int, shop_id: int) -> dict:
    logger.info("API-JSON parse scheduled product=%s shop=%s", product_id, shop_id)
    return {"ok": True}


@shared_task(queue="heavy", soft_time_limit=180)
def parse_playwright(product_id: int, shop_id: int) -> dict:
    logger.info("Playwright parse scheduled product=%s shop=%s", product_id, shop_id)
    return {"ok": True}


def _dispatch_for_shop(product_id: int, shop: Shop):
    """Диспетчер парсеров по типу магазина"""
    # Получаем URL из существующего оффера
    offer = Offer.objects.filter(product_id=product_id, shop=shop).first()
    if not offer:
        logger.warning(f"No offer found for product {product_id} in shop {shop.id}")
        return

    if shop.parser_type == "playwright":
        parse_playwright.delay(product_id, shop.id)
    elif shop.parser_type == "beautifulsoup" and "hobbygames.ru" in shop.domain:
        parse_hobbygames_product.delay(product_id, shop.id, offer.url)
    else:
        parse_api_json.delay(product_id, shop.id)


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
    # после обновления — проверим алёрты
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
    """Проверить и сработать пользовательские алёрты по продукту."""
    # текущая минимальная цена
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
        # TODO: интеграция с ботом (HTTP запрос к сервису бота по X-Service-Token)
        logger.info(
            "ALERT TRIGGER user=%s product=%s price=%s url=%s",
            alert.user_id,
            product_id,
            min_offer.price,
            min_offer.url,
        )
        alert.last_triggered_at = timezone.now()
        alert.is_active = False  # авто-выключение после срабатывания
        alert.save(update_fields=["last_triggered_at", "is_active"])
        count += 1
    return count
