import logging
from typing import Iterable

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from user.models import User, UserFavorite

from .constants import (
    BOT_SEND_ALERT_URL,
    BOT_SEND_MESSAGE_URL,
    DEFAULT_BATCH_LIMIT,
    DEFAULT_DISCOVERY_LIMIT,
    DEFAULT_MAX_PAGES_PER_CALL,
    DEFAULT_MAX_TOTAL_PAGES,
    DEFAULT_TIMEOUT,
    REFRESH_COUNTDOWN,
)
from .integrations.bot_client import BotClient
from .models import Offer, PriceAlert, Shop
from .services.universal_parser_service import UniversalParserService

logger = logging.getLogger("parser_results")

_bot_client: BotClient | None = None


def get_bot_client() -> BotClient:
    global _bot_client
    if _bot_client is None:
        _bot_client = BotClient(
            service_token=settings.BOT_SERVICE_TOKEN or "",
            send_message_url=BOT_SEND_MESSAGE_URL,
            send_alert_url=BOT_SEND_ALERT_URL,
            timeout=DEFAULT_TIMEOUT,
        )
    return _bot_client


@shared_task(
    queue="light",
    autoretry_for=(requests.exceptions.RequestException, Exception),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
)
def parse_product_universal(product_id: int, shop_id: int, url: str = None):
    """Универсальный парсинг товара"""
    try:
        service = UniversalParserService()
        result = service.parse_product(product_id, shop_id, url)

        if result.ok and result.value:
            logger.info(
                f"Updated product {product_id}: "
                f"{result.value.get('price')} {result.value.get('title', '')}"
            )

        return result.to_dict()
    except Exception as e:
        logger.error("Parse error for product %s: %s", product_id, e)
        return {"ok": False, "error": str(e)}


@shared_task(queue="light")
def bulk_parse_all_shops() -> dict:
    """Массовый парсинг всех товаров по всем магазинам (раз в 3 дня)"""
    try:
        total_parsed = 0
        results = {}

        shops = Shop.objects.filter(is_active=True)

        for shop in shops:
            logger.info(
                f"Starting bulk parse for shop: {shop.name} ({shop.parser_type})"
            )

            offers = Offer.objects.filter(shop=shop)

            if offers.exists():
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
                discover_products_for_shop.delay(shop.id, DEFAULT_DISCOVERY_LIMIT)
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
    """Диспетчер парсеров по типу магазина - универсальный"""
    offer = Offer.objects.filter(product_id=product_id, shop=shop).first()
    url = offer.url if offer else None
    parse_product_universal.delay(product_id, shop.id, url)


@shared_task(queue="light")
def refresh_product(product_id: int, user_telegram_id: int = None) -> int:
    """Запланировать обновление по всем активным магазинам, где есть офферы продукта."""
    shops: Iterable[Shop] = Shop.objects.filter(
        is_active=True, offer__product_id=product_id
    ).distinct()
    count = 0

    for shop in shops:
        _dispatch_for_shop(product_id, shop)
        count += 1

    logger.info("Queued %s parse jobs for product=%s", count, product_id)

    if user_telegram_id:
        send_refresh_result.apply_async(
            args=[product_id, user_telegram_id],
            countdown=REFRESH_COUNTDOWN,
        )
    return count


@shared_task(queue="light")
def send_refresh_result(product_id: int, user_telegram_id: int):
    """Отправить результат обновления пользователю"""
    try:
        min_offer = (
            Offer.objects.filter(product_id=product_id, is_available=True)
            .order_by("price")
            .first()
        )

        if min_offer:
            message = f"💰 Обновлено! Цена: {min_offer.price} {min_offer.currency}"
        else:
            message = "❌ Товар больше не доступен"

        get_bot_client().send_message(user_telegram_id, message)
        check_alerts_for_product.delay(product_id)

    except Exception as e:
        logger.error(f"Failed to send refresh result: {e}")


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
            if not alert.user.telegram_id:
                logger.warning(
                    f"User {alert.user_id} has no telegram_id, skipping alert"
                )
                continue

            alert_data = {
                "user_id": alert.user.telegram_id,
                "product_id": product_id,
                "price": float(min_offer.price),
                "currency": min_offer.currency,
                "url": min_offer.url,
                "shop_name": min_offer.shop.name,
                "alert_id": alert.id,
            }

            get_bot_client().send_alert(alert_data)

            logger.info(
                "ALERT TRIGGER user=%s product=%s price=%s url=%s",
                alert.user.telegram_id,
                product_id,
                min_offer.price,
                min_offer.url,
            )
            alert.last_triggered_at = timezone.now()
            alert.is_active = False
            alert.save(update_fields=["last_triggered_at", "is_active"])
            count += 1

        except Exception as e:
            logger.error(f"Failed to send alert to bot: {e}")

    return count


@shared_task(
    queue="heavy",
    autoretry_for=(requests.exceptions.RequestException, Exception),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
)
def discover_products_for_shop(
    shop_id: int, limit: int = DEFAULT_DISCOVERY_LIMIT
) -> dict:
    """Обнаружение новых товаров для магазина"""
    try:
        service = UniversalParserService()
        page_start = 1
        total_found = 0

        logger.info(f"Starting discovery for shop {shop_id}, target limit: {limit}")

        while total_found < limit and page_start <= DEFAULT_MAX_TOTAL_PAGES:
            remaining = limit - total_found
            batch_limit = min(remaining, DEFAULT_BATCH_LIMIT)

            logger.info(
                f"Batch: page_start={page_start}, batch_limit={batch_limit}, "
                f"total_found={total_found}"
            )

            result = service.discover_products(
                shop_id,
                limit=batch_limit,
                page_start=page_start,
                max_pages=DEFAULT_MAX_PAGES_PER_CALL,
            )

            if not result.get("ok"):
                logger.error(f"Discovery failed at page {page_start}: {result}")
                return result

            found = result.get("products_found", 0)
            total_found += found

            logger.info(f"Batch result: found={found}, total_found={total_found}")

            if found == 0:
                logger.info("No more products found, stopping")
                break

            page_start += DEFAULT_MAX_PAGES_PER_CALL

        logger.info(f"Discovery completed: total_found={total_found}")
        return {"ok": True, "total_found": total_found}

    except Exception as e:
        logger.error(f"discover_products_for_shop error: {e}")
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


@shared_task(
    queue="light",
    autoretry_for=(requests.exceptions.RequestException,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def health_check_parsers() -> dict:
    """Проверка здоровья всех парсеров"""
    service = UniversalParserService()
    results = {}

    for parser_type, endpoint in service.parser_service.parser_endpoints.items():
        try:
            response = requests.get(f"{endpoint}/health", timeout=DEFAULT_TIMEOUT)
            results[parser_type] = {
                "status": "ok" if response.status_code == 200 else "error",
                "response_time": response.elapsed.total_seconds(),
                "status_code": response.status_code,
            }
        except Exception as e:
            results[parser_type] = {"status": "error", "error": str(e)}

    return {"ok": True, "parsers": results}
