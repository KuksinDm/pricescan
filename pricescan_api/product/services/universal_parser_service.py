# pricescan_api/product/services/universal_parser_service.py
import logging
from typing import Dict, List

from ..models import Offer, Product, Shop
from .offer_service import OfferService
from .parser_service import ParserService
from .product_service import ProductService

logger = logging.getLogger("parser_results")


class UniversalParserService:
    """Оркестратор для всех парсеров"""

    def __init__(self):
        self.parser_service = ParserService()
        self.product_service = ProductService()
        self.offer_service = OfferService()

    def parse_product(self, product_id: int, shop_id: int, url: str = None) -> Dict:
        """Универсальный парсинг товара"""
        try:
            shop = Shop.objects.get(id=shop_id)

            if not url:
                offer = Offer.objects.filter(product_id=product_id, shop=shop).first()
                if not offer:
                    return {"ok": False, "error": "No offer found and no URL provided"}
                url = offer.url

            # Получаем данные от парсера
            parser_result = self.parser_service.parse_product(
                shop.parser_type, url, shop.name, shop.domain
            )

            if not parser_result.get("ok", False):
                return parser_result

            # Обновляем товар
            product = Product.objects.get(id=product_id)
            updated_fields = self.product_service.update_product_info(
                product, parser_result
            )

            # Обновляем оффер
            price = parser_result.get("price_rub")
            if price:
                self.offer_service.update_or_create_offer(product, shop, price, url)

            return {
                "ok": True,
                "product_id": product_id,
                "shop_id": shop.id,
                "price": price,
                "title": parser_result.get("title", ""),
                "updated_fields": updated_fields,
            }

        except Exception as e:
            logger.error(f"Parse product error: {e}")
            return {"ok": False, "error": str(e)}

    def discover_products(
        self,
        shop_id: int,
        query: str = "настольная игра",
        limit: int = 1000,
        page_start: int = 1,
        max_pages: int | None = 12,
    ) -> Dict:
        """Обнаружение новых товаров"""
        try:
            logger.info(
                f"discover_products called: shop_id={shop_id}, query={query}, "
                f"limit={limit}"
            )
            shop = Shop.objects.get(id=shop_id)
            shop_url = shop.domain
            logger.info(
                f"Shop found: {shop.name}, parser_type={shop.parser_type}, "
                f"domain={shop.domain}"
            )

            # Парсинг каталога через парсер
            logger.info(
                f"Calling parser_service.parse_catalog with: "
                f"parser_type={shop.parser_type}, shop_url={shop_url}, "
                f"limit={limit}, shop_name={shop.name}"
            )
            catalog_result = self.parser_service.parse_catalog(
                shop.parser_type,
                shop_url,
                limit=limit,           # пробрасываем фактический лимит
                shop_name=shop.name,
                page_start=page_start, # новый аргумент
                max_pages=max_pages,   # новый аргумент
                detail=True,
            )
            logger.info(f"Catalog result: {catalog_result}")
            if not catalog_result.get("ok", False):
                logger.error(f"Catalog parsing failed: {catalog_result}")
                return catalog_result

            # Создаем товары
            products_data = catalog_result.get("products", [])
            created_stats = self._create_products_from_data(products_data, shop)

            return {"ok": True, "products_found": len(products_data), **created_stats}

        except Exception as e:
            logger.error(f"Discover products error: {e}")
            return {"ok": False, "error": str(e)}

    def _create_products_from_data(self, products_data: List[Dict], shop) -> Dict:
        """Создание товаров из данных парсера"""
        stats = {
            "products_created": 0,
            "offers_created": 0,
            "products_updated": 0,
            "errors": 0,
        }

        for product_data in products_data:
            try:
                result = self.product_service.create_or_update_product_from_data(
                    product_data, shop
                )
                if result["created"]:
                    stats["products_created"] += 1
                else:
                    stats["products_updated"] += 1

                # Создаем оффер
                price = product_data.get("price_rub")
                url = product_data.get("url", "")
                if price and url:
                    self.offer_service.update_or_create_offer(
                        result["product"], shop, price, url
                    )
                    stats["offers_created"] += 1

            except Exception as e:
                logger.error(f"Error creating product from data: {e}")
                stats["errors"] += 1

        return stats
