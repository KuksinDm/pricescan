import logging
from typing import Any, Dict, Optional

import aiohttp
from cachetools import TTLCache

from .constants import (
    DEFAULT_LIMIT,
    DEFAULT_OFFERS_LIMIT,
    DEFAULT_TIMEOUT,
    JWT_CACHE_MAXSIZE,
    JWT_CACHE_TTL,
)

logger = logging.getLogger(__name__)


class ApiClient:
    """HTTP клиент для взаимодействия с Django API"""

    def __init__(self, base_url: str, service_token: str):
        self.base_url = base_url.rstrip("/") + "/"
        self.service_token = service_token
        self._session: Optional[aiohttp.ClientSession] = None
        self._access_by_tg: TTLCache[int, str] = TTLCache(
            maxsize=JWT_CACHE_MAXSIZE, ttl=JWT_CACHE_TTL
        )

    @property
    def session(self) -> aiohttp.ClientSession:
        """Получает или создает HTTP сессию"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            )
        return self._session

    async def close(self):
        """Закрывает HTTP сессию"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def ensure_jwt(
        self,
        *,
        telegram_id: int,
        telegram_username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
        language_code: Optional[str],
    ) -> Optional[str]:
        """Получает JWT токен для пользователя"""
        if telegram_id in self._access_by_tg:
            return self._access_by_tg[telegram_id]

        if not self.service_token:
            logger.warning("Service token not configured; skipping JWT fetch")
            return None

        url = self.base_url + "auth/jwt/by-telegram/"
        headers = {"X-Service-Token": self.service_token}
        payload = {
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "first_name": (first_name or ""),
            "last_name": (last_name or ""),
            "language_code": language_code,
        }

        try:
            async with self.session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    await _safe_text(resp)
                    logger.warning(
                        "JWT fetch failed for user %s: %s", telegram_id, resp.status
                    )
                    return None

                data = await resp.json()
                access = data.get("access")
                if access:
                    self._access_by_tg[telegram_id] = access
                    logger.debug("JWT token obtained for user %s", telegram_id)
                return access

        except Exception as e:
            logger.exception("Failed to get JWT for user %s: %s", telegram_id, e)
            return None

    async def get_cheapest(self, query: str) -> Optional[Dict[str, Any]]:
        """Получает самые дешевые предложения по запросу"""
        url = self.base_url + "products/cheapest/"
        params = {"q": query}

        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(
                        "Failed to get cheapest for query '%s': %s", query, resp.status
                    )
                    return None
                return await resp.json()
        except Exception as e:
            logger.exception("Error getting cheapest for query '%s': %s", query, e)
            return None

    async def get_offers(self, product_id: int, limit: int = DEFAULT_OFFERS_LIMIT):
        """Получает список предложений для товара"""
        url = self.base_url + "offers/"
        params = {
            "product": str(product_id),
            "is_available": "true",
            "ordering": "price",
            "limit": str(limit),
        }

        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(
                        "Failed to get offers for product %s: %s",
                        product_id,
                        resp.status,
                    )
                    return []

                data = await resp.json()
                items = data.get("results", data)
                return list(items)[:limit]
        except Exception as e:
            logger.exception("Error getting offers for product %s: %s", product_id, e)
            return []

    async def get_discounts(self, limit: int = DEFAULT_LIMIT):
        """Получает товары со скидками"""
        url = self.base_url + "offers/discounts/"
        params = {"limit": str(limit)}

        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("Failed to get discounts: %s", resp.status)
                    return []

                data = await resp.json()
                return data.get("results", data)
        except Exception as e:
            logger.exception("Error getting discounts: %s", e)
            return []

    async def refresh_product(
        self, product_id: int, *, telegram_id: Optional[int] = None
    ) -> bool:
        """Запрашивает обновление цен для товара"""
        url = self.base_url + f"products/{product_id}/refresh/"
        headers = self._get_auth_headers(telegram_id) if telegram_id else {}
        params = {}
        if telegram_id:
            params["user_telegram_id"] = telegram_id
        try:
            async with self.session.post(url, headers=headers) as resp:
                success = resp.status == 202
                if not success:
                    logger.warning(
                        "Failed to refresh product %s: %s", product_id, resp.status
                    )
                return success
        except Exception as e:
            logger.exception("Error refreshing product %s: %s", product_id, e)
            return False

    # Избранное
    async def add_favorite(self, product_id: int, *, telegram_id: int) -> bool:
        """Добавляет товар в избранное"""
        url = self.base_url + "favorites/"
        headers = self._get_auth_headers(telegram_id)
        payload = {"product": int(product_id)}

        try:
            async with self.session.post(url, json=payload, headers=headers) as resp:
                success = resp.status in (200, 201)
                if not success:
                    logger.warning(
                        "Failed to add favorite for user %s, product %s: %s",
                        telegram_id,
                        product_id,
                        resp.status,
                    )
                return success
        except Exception as e:
            logger.exception(
                "Error adding favorite for user %s, product %s: %s",
                telegram_id,
                product_id,
                e,
            )
            return False

    async def list_favorites(self, *, telegram_id: int, limit: int = DEFAULT_LIMIT):
        """Получает список избранных товаров"""
        url = self.base_url + "favorites/"
        headers = self._get_auth_headers(telegram_id)
        params = {"limit": str(limit)}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(
                        "Failed to list favorites for user %s: %s",
                        telegram_id,
                        resp.status,
                    )
                    return []

                data = await resp.json()
                return data.get("results", data)
        except Exception as e:
            logger.exception("Error listing favorites for user %s: %s", telegram_id, e)
            return []

    async def delete_favorite(self, fav_id: int, *, telegram_id: int) -> bool:
        """Удаляет товар из избранного"""
        url = self.base_url + f"favorites/{fav_id}/"
        headers = self._get_auth_headers(telegram_id)

        try:
            async with self.session.delete(url, headers=headers) as resp:
                success = resp.status in (200, 204)
                if not success:
                    logger.warning(
                        "Failed to delete favorite %s for user %s: %s",
                        fav_id,
                        telegram_id,
                        resp.status,
                    )
                return success
        except Exception as e:
            logger.exception(
                "Error deleting favorite %s for user %s: %s", fav_id, telegram_id, e
            )
            return False

    # Подписки
    async def create_alert(
        self,
        *,
        telegram_id: int,
        product_id: int,
        threshold_price: float,
        currency: str = "RUB",
        shop_id: int | None = None,
    ) -> bool:
        """Создает алерт на снижение цены"""
        url = self.base_url + "price-alerts/"
        headers = self._get_auth_headers(telegram_id)
        payload = {
            "product": product_id,
            "threshold_price": str(threshold_price),
            "currency": currency,
        }
        if shop_id:
            payload["shop"] = shop_id

        try:
            async with self.session.post(url, json=payload, headers=headers) as resp:
                success = resp.status in (200, 201)
                if not success:
                    logger.warning(
                        "Failed to create alert for user %s, product %s: %s",
                        telegram_id,
                        product_id,
                        resp.status,
                    )
                return success
        except Exception as e:
            logger.exception(
                "Error creating alert for user %s, product %s: %s",
                telegram_id,
                product_id,
                e,
            )
            return False

    async def list_alerts(self, *, telegram_id: int, limit: int = DEFAULT_LIMIT):
        """Получает список алертов пользователя"""
        url = self.base_url + "price-alerts/"
        headers = self._get_auth_headers(telegram_id)
        params = {"limit": str(limit)}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(
                        "Failed to list alerts for user %s: %s",
                        telegram_id,
                        resp.status,
                    )
                    return []

                data = await resp.json()
                return data.get("results", data)
        except Exception as e:
            logger.exception("Error listing alerts for user %s: %s", telegram_id, e)
            return []

    async def toggle_alert(self, alert_id: int, *, telegram_id: int) -> bool:
        """Переключает состояние алерта"""
        url = self.base_url + f"price-alerts/{alert_id}/toggle/"
        headers = self._get_auth_headers(telegram_id)

        try:
            async with self.session.post(url, headers=headers) as resp:
                success = resp.status == 200
                if not success:
                    logger.warning(
                        "Failed to toggle alert %s for user %s: %s",
                        alert_id,
                        telegram_id,
                        resp.status,
                    )
                return success
        except Exception as e:
            logger.exception(
                "Error toggling alert %s for user %s: %s", alert_id, telegram_id, e
            )
            return False

    async def delete_alert(self, alert_id: int, *, telegram_id: int) -> bool:
        """Удаляет алерт"""
        url = self.base_url + f"price-alerts/{alert_id}/"
        headers = self._get_auth_headers(telegram_id)

        try:
            async with self.session.delete(url, headers=headers) as resp:
                success = resp.status in (200, 204)
                if not success:
                    logger.warning(
                        "Failed to delete alert %s for user %s: %s",
                        alert_id,
                        telegram_id,
                        resp.status,
                    )
                return success
        except Exception as e:
            logger.exception(
                "Error deleting alert %s for user %s: %s", alert_id, telegram_id, e
            )
            return False

    async def update_alert_price(
        self, alert_id: int, *, telegram_id: int, threshold_price: float
    ) -> bool:
        """Изменяет пороговую цену алерта"""
        url = self.base_url + f"price-alerts/{alert_id}/"
        headers = self._get_auth_headers(telegram_id)
        payload = {"threshold_price": str(threshold_price)}

        try:
            async with self.session.patch(url, json=payload, headers=headers) as resp:
                success = resp.status in (200, 202)
                if not success:
                    logger.warning(
                        "Failed to update alert price %s for user %s: %s",
                        alert_id,
                        telegram_id,
                        resp.status,
                    )
                return success
        except Exception as e:
            logger.exception(
                "Error updating alert price %s for user %s: %s",
                alert_id,
                telegram_id,
                e,
            )
            return False

    async def list_favorites_page(
        self, *, telegram_id: int, limit: int = DEFAULT_OFFERS_LIMIT, offset: int = 0
    ):
        """Получает страницу избранных товаров с пагинацией"""
        url = self.base_url + "favorites/"
        headers = self._get_auth_headers(telegram_id)
        params = {"limit": str(limit), "offset": str(offset)}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(
                        "Failed to get favorites page for user %s: %s",
                        telegram_id,
                        resp.status,
                    )
                    return [], None, None

                data = await resp.json()
                items = data.get("results", data)
                prev_off = offset - limit if offset > 0 else None
                next_off = offset + limit if data.get("next") else None
                return items, prev_off, next_off
        except Exception as e:
            logger.exception(
                "Error getting favorites page for user %s: %s", telegram_id, e
            )
            return [], None, None

    async def list_alerts_page(
        self, *, telegram_id: int, limit: int = DEFAULT_OFFERS_LIMIT, offset: int = 0
    ):
        """Получает страницу алертов с пагинацией"""
        url = self.base_url + "price-alerts/"
        headers = self._get_auth_headers(telegram_id)
        params = {"limit": str(limit), "offset": str(offset)}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(
                        "Failed to get alerts page for user %s: %s",
                        telegram_id,
                        resp.status,
                    )
                    return [], None, None

                data = await resp.json()
                items = data.get("results", data)
                prev_off = offset - limit if offset > 0 else None
                next_off = offset + limit if data.get("next") else None
                return items, prev_off, next_off
        except Exception as e:
            logger.exception(
                "Error getting alerts page for user %s: %s", telegram_id, e
            )
            return [], None, None

    def _get_auth_headers(self, telegram_id: int) -> dict[str, str]:
        """Получает заголовки авторизации для пользователя"""
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        return headers


async def _safe_text(resp: aiohttp.ClientResponse) -> str:
    """Безопасно получает текст ответа"""
    try:
        return await resp.text()
    except Exception:
        return "<no text>"
