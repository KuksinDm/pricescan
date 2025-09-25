# pricescan_api/product/services/offer_service.py
import logging
from decimal import Decimal
from typing import Dict

from ..models import Offer, PriceHistory, Shop

logger = logging.getLogger("parser_results")


class OfferService:
    """Сервис для работы с офферами"""

    def update_or_create_offer(self, product, shop: Shop, price: int, url: str) -> Dict:
        """Обновление или создание оффера"""
        offer, created = Offer.objects.get_or_create(
            product=product,
            shop=shop,
            defaults={
                "price": Decimal(str(price)),
                "currency": "RUB",
                "url": url,
                "is_available": True,
            },
        )

        if not created and offer.price != Decimal(str(price)):
            # Сохраняем историю цен
            PriceHistory.objects.create(
                offer=offer, price=offer.price, currency=offer.currency
            )

            # Обновляем цену
            offer.price = Decimal(str(price))
            offer.is_available = True
            offer.save(update_fields=["price", "is_available", "last_updated"])

        return {
            "created": created,
            "offer": offer,
        }
