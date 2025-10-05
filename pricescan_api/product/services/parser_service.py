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
        }
        logger.info(
            f"ParserService initialized with endpoints: {self.parser_endpoints}"
        )

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
        self,
        parser_type: str,
        shop_url: str,
        limit: int,
        shop_name: str,
        page_start: int = 1,
        max_pages: int | None = 100,
        detail: bool = True,
    ) -> dict:
        """Парсинг каталога через внешний сервис (c пагинацией и батчем страниц)."""
        try:
            logger.info(
                f"parse_catalog called: parser_type={parser_type}, "
                f"shop_url={shop_url}, limit={limit}, shop_name={shop_name}, "
                f"page_start={page_start}, max_pages={max_pages}, detail={detail}"
            )

            endpoint = self.parser_endpoints.get(parser_type)
            if not endpoint:
                logger.error(f"Unsupported parser type: {parser_type}")
                return {"ok": False, "error": f"Unsupported parser type: {parser_type}"}

            # # !!!!!!!!!!!!Отключаем Playwright парсер для этого магазина!!!!!!!!!!!!
            # if parser_type == "playwright":
            #     logger.info(f"Playwright parser disabled, skipping {shop_name}")
            #     return {
            #         "ok": False,
            #         "error": "Playwright parser temporarily disabled",
            #     }

            logger.info(f"Sending request to {endpoint}/parse/catalog")

            # Таймаут под размер батча страниц (например, ~60 сек на страницу), с потолком
            pages = int(max_pages or 100)
            estimated_products = pages * 48  # 48 товаров на страницу
            timeout_sec = min(3600, max(300, estimated_products * 3))  # 3 секунды на товар

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
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response content: {response.text[:500]}")
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
            logger.info(
                f"Catalog result: success={catalog_result.get('success')}, "
                f"total_found={catalog_result.get('total_found')}"
            )
            return self._process_catalog_response(catalog_result)

        except Exception as e:
            logger.error(f"Catalog parse failed: {str(e)}")
            return {"ok": False, "error": f"Catalog parse failed: {str(e)}"}

    # def parse_catalog(
    #     self, parser_type: str, shop_url: str, limit: int, shop_name: str
    # ) -> dict:
    #     """Парсинг каталога через внешний сервис"""
    #     try:
    #         logger.info(
    #             f"parse_catalog called: parser_type={parser_type}, "
    #             f"shop_url={shop_url}, "
    #             f"limit={limit}, shop_name={shop_name}"
    #         )

    #         endpoint = self.parser_endpoints.get(parser_type)
    #         if not endpoint:
    #             logger.error(f"Unsupported parser type: {parser_type}")
    #             return {"ok": False, "error": f"Unsupported parser type: {parser_type}"}

    #         logger.info(f"Sending request to {endpoint}/parse/catalog")

    #         # Добавляем таймаут и обработку ошибок
    #         try:
    #             response = requests.post(
    #                 f"{endpoint}/parse/catalog",
    #                 json={
    #                     "shop_url": shop_url,
    #                     "limit": limit,
    #                     "shop_name": shop_name,
    #                     "parser_type": parser_type,
    #                 },
    #                 timeout=300,
    #             )
    #             logger.info(f"Response status: {response.status_code}")
    #             logger.info(
    #                 f"Response content: {response.text[:500]}"
    #             )  # Первые 500 символов

    #         except requests.exceptions.ConnectionError as e:
    #             logger.error(f"Connection error to {endpoint}: {e}")
    #             return {"ok": False, "error": f"Connection error: {e}"}
    #         except requests.exceptions.Timeout as e:
    #             logger.error(f"Timeout error to {endpoint}: {e}")
    #             return {"ok": False, "error": f"Timeout error: {e}"}
    #         except Exception as e:
    #             logger.error(f"Request error to {endpoint}: {e}")
    #             return {"ok": False, "error": f"Request error: {e}"}

    #         if response.status_code != 200:
    #             logger.error(f"Parser API failed: {response.status_code}")
    #             return {
    #                 "ok": False,
    #                 "error": f"Parser API failed: {response.status_code}",
    #             }

    #         catalog_result = response.json()
    #         logger.info(
    #             f"Catalog result: success={catalog_result.get('success')}, "
    #             f"total_found={catalog_result.get('total_found')}"
    #         )
    #         return self._process_catalog_response(catalog_result)

    #     except Exception as e:
    #         logger.error(f"Catalog parse failed: {str(e)}")
    #         return {"ok": False, "error": f"Catalog parse failed: {str(e)}"}

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
