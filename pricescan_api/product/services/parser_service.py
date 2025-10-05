import logging
from typing import Dict

import requests

from ..constants import (
    BEAUTIFULSOUP_TIMEOUT,
    DEFAULT_MAX_PAGES,
    DEFAULT_PRODUCTS_PER_PAGE,
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
    PLAYWRIGHT_TIMEOUT,
    TIMEOUT_MULTIPLIER,
)

logger = logging.getLogger("parser_results")


class ParserService:
    """Сервис для работы с внешними парсерами"""

    def __init__(self):
        self.parser_endpoints = {
            "beautifulsoup": "http://pricescan_parser:8000",
            "playwright": "http://pricescan_playwright:8000",
        }

    def parse_product(
        self, parser_type: str, url: str, shop_name: str, shop_url: str
    ) -> Dict:
        """Парсинг товара через внешний сервис"""
        try:
            endpoint = self.parser_endpoints.get(parser_type)
            if not endpoint:
                return {"ok": False, "error": f"Unsupported parser type: {parser_type}"}

            response = self._make_request(
                endpoint, parser_type, url, shop_name, shop_url
            )

            if response.status_code != 200:
                return {
                    "ok": False,
                    "error": f"Parser service failed: {response.status_code}",
                }

            result = response.json()
            return self._process_parser_response(result)

        except requests.RequestException as e:
            return {"ok": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"ok": False, "error": f"Parser call failed: {str(e)}"}

    def parse_catalog(
        self,
        parser_type: str,
        shop_url: str,
        limit: int,
        shop_name: str,
        page_start: int = 1,
        max_pages: int | None = DEFAULT_MAX_PAGES,
        detail: bool = True,
    ) -> dict:
        """Парсинг каталога через внешний сервис"""
        try:
            endpoint = self.parser_endpoints.get(parser_type)
            if not endpoint:
                logger.error(f"Unsupported parser type: {parser_type}")
                return {"ok": False, "error": f"Unsupported parser type: {parser_type}"}

            pages = int(max_pages or DEFAULT_MAX_PAGES)
            estimated_products = pages * DEFAULT_PRODUCTS_PER_PAGE
            timeout_sec = min(
                MAX_TIMEOUT,
                max(DEFAULT_TIMEOUT, estimated_products * TIMEOUT_MULTIPLIER),
            )

            try:
                response = requests.post(
                    f"{endpoint}/parse/catalog",
                    json={
                        "shop_url": shop_url,
                        "limit": limit,
                        "shop_name": shop_name,
                        "parser_type": parser_type,
                        "page_start": page_start,
                        "max_pages": max_pages,
                        "detail": detail,
                    },
                    timeout=timeout_sec,
                )
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error to {endpoint}: {e}")
                return {"ok": False, "error": f"Connection error: {e}"}
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout error to {endpoint}: {e}")
                return {"ok": False, "error": f"Timeout error: {e}"}
            except Exception as e:
                logger.error(f"Request error to {endpoint}: {e}")
                return {"ok": False, "error": f"Request error: {e}"}

            if response.status_code != 200:
                logger.error(f"Parser API failed: {response.status_code}")
                return {
                    "ok": False,
                    "error": f"Parser API failed: {response.status_code}",
                }

            catalog_result = response.json()
            return self._process_catalog_response(catalog_result)

        except Exception as e:
            logger.error(f"Catalog parse failed: {str(e)}")
            return {"ok": False, "error": f"Catalog parse failed: {str(e)}"}

    def _make_request(
        self, endpoint: str, parser_type: str, url: str, shop_name: str, shop_url: str
    ):
        """Создание HTTP запроса к парсеру"""
        timeout = (
            PLAYWRIGHT_TIMEOUT if parser_type == "playwright" else BEAUTIFULSOUP_TIMEOUT
        )

        if parser_type == "playwright":
            return requests.post(
                f"{endpoint}/parse/product",
                json={
                    "url": url,
                    "shop_name": shop_name,
                    "shop_url": shop_url,
                },
                timeout=timeout,
            )
        else:
            return requests.post(
                f"{endpoint}/parse/product",
                json={
                    "url": url,
                    "parser_type": parser_type,
                    "shop_name": shop_name,
                    "shop_url": shop_url,
                },
                timeout=timeout,
            )

    def _process_parser_response(self, result: Dict) -> Dict:
        """Обработка ответа парсера"""
        if result.get("success"):
            return {
                "ok": True,
                "title": result.get("data", {}).get("title"),
                "price_rub": result.get("data", {}).get("price_rub"),
                "description": result.get("data", {}).get("description"),
                "manufacturer": result.get("data", {}).get("manufacturer"),
                "players": result.get("data", {}).get("players"),
                "age": result.get("data", {}).get("age"),
                "play_time": result.get("data", {}).get("play_time"),
                "external_id": result.get("data", {}).get("external_id"),
                "image_url": result.get("data", {}).get("image_url"),
            }
        else:
            return {
                "ok": False,
                "error": result.get("error", "Unknown parser error"),
            }

    def _process_catalog_response(self, result: Dict) -> Dict:
        """Обработка ответа парсинга каталога"""
        if result.get("success"):
            return {
                "ok": True,
                "products": result.get("products", []),
            }
        else:
            return {
                "ok": False,
                "error": result.get("error", "Catalog parse failed"),
            }
