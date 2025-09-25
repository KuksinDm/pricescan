# pricescan_api/product/services/parser_service.py
import logging
from typing import Dict

import requests

logger = logging.getLogger("parser_results")


class ParserService:
    """Сервис для работы с внешними парсерами"""

    def __init__(self):
        self.parser_endpoints = {
            "beautifulsoup": "http://pricescan_parser:8000",
            "playwright": "http://pricescan_playwright:8000",
            "api_json": "http://pricescan_parser:8000",
        }

    def parse_product(
        self, parser_type: str, url: str, shop_name: str, shop_url: str
    ) -> Dict:
        """Парсинг товара через внешний сервис"""
        try:
            endpoint = self.parser_endpoints.get(parser_type)
            if not endpoint:
                return {"ok": False, "error": f"Unsupported parser type: {parser_type}"}

            # Формируем запрос в зависимости от типа парсера
            if parser_type == "playwright":
                response = requests.post(
                    f"{endpoint}/parse/product",
                    json={
                        "url": url,
                        "shop_name": shop_name,
                        "shop_url": shop_url,
                    },
                    timeout=60,
                )
            else:
                response = requests.post(
                    f"{endpoint}/parse/product",
                    json={
                        "url": url,
                        "parser_type": parser_type,
                        "shop_name": shop_name,
                        "shop_url": shop_url,
                    },
                    timeout=30,
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
        self, parser_type: str, shop_url: str, limit: int, shop_name: str
    ) -> dict:
        """Парсинг каталога через внешний сервис"""
        try:
            endpoint = self.parser_endpoints.get(parser_type)
            if not endpoint:
                return {"ok": False, "error": f"Unsupported parser type: {parser_type}"}

            response = requests.post(
                f"{endpoint}/parse/catalog",  # ✅ ПРАВИЛЬНО!
                json={
                    "shop_url": shop_url,  # ✅ ПРАВИЛЬНО!
                    "limit": limit,
                    "shop_name": shop_name,
                },
                timeout=60,
            )

            if response.status_code != 200:
                return {
                    "ok": False,
                    "error": f"Parser API failed: {response.status_code}",
                }

            catalog_result = response.json()
            return self._process_catalog_response(catalog_result)  # ✅ ПРАВИЛЬНО!

        except requests.RequestException as e:
            return {"ok": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"ok": False, "error": f"Catalog parse failed: {str(e)}"}

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
