import logging
from typing import Iterable

from celery import shared_task
from django.utils import timezone

from .models import Offer, PriceAlert, Shop

logger = logging.getLogger("parser_results")


@shared_task(queue="light")
def parse_bs4(product_id: int, shop_id: int) -> dict:
    # тут должен быть реальный парсинг
    logger.info("BS4 parse scheduled product=%s shop=%s", product_id, shop_id)
    return {"ok": True}


@shared_task(queue="light")
def parse_api_json(product_id: int, shop_id: int) -> dict:
    logger.info("API-JSON parse scheduled product=%s shop=%s", product_id, shop_id)
    return {"ok": True}


@shared_task(queue="heavy", soft_time_limit=180)
def parse_playwright(product_id: int, shop_id: int) -> dict:
    logger.info("Playwright parse scheduled product=%s shop=%s", product_id, shop_id)
    return {"ok": True}


def _dispatch_for_shop(product_id: int, shop: Shop):
    if shop.parser_type == "playwright":
        parse_playwright.delay(product_id, shop.id)
    elif shop.parser_type == "beautifulsoup":
        parse_bs4.delay(product_id, shop.id)
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
    """Проверить и сработать пользоват. алёрты по продукту."""
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
