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
    def __init__(self, base_url: str, service_token: str):
        self.base_url = base_url.rstrip("/") + "/"
        self.service_token = service_token
        self._session: Optional[aiohttp.ClientSession] = None
        self._access_by_tg: TTLCache[int, str] = TTLCache(
            maxsize=JWT_CACHE_MAXSIZE, ttl=JWT_CACHE_TTL
        )

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            )
        return self._session

    async def close(self):
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
        url = self.base_url + "products/cheapest/"
        params = {"q": query}

        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
        except Exception as e:
            logger.error("API request failed: %s - %s", url, e)
            return None

    async def get_offers(self, product_id: int, limit: int = DEFAULT_OFFERS_LIMIT):
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
                    return []

                data = await resp.json()
                items = data.get("results", data)
                return list(items)[:limit]
        except Exception:
            return []

    async def get_discounts(self, limit: int = DEFAULT_LIMIT):
        url = self.base_url + "offers/discounts/"
        params = {"limit": str(limit)}

        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()
                return data.get("results", data)
        except Exception:
            return []

    async def refresh_product(
        self, product_id: int, *, telegram_id: Optional[int] = None
    ) -> bool:
        url = self.base_url + f"products/{product_id}/refresh/"
        headers = self._get_auth_headers(telegram_id) if telegram_id else {}
        try:
            async with self.session.post(url, headers=headers) as resp:
                return resp.status == 202
        except Exception:
            return False

    async def add_favorite(self, product_id: int, *, telegram_id: int) -> bool:
        url = self.base_url + "favorites/"
        headers = self._get_auth_headers(telegram_id)
        payload = {"product": int(product_id)}

        try:
            async with self.session.post(url, json=payload, headers=headers) as resp:
                return resp.status in (200, 201)
        except Exception:
            return False

    async def list_favorites(self, *, telegram_id: int, limit: int = DEFAULT_LIMIT):
        url = self.base_url + "favorites/"
        headers = self._get_auth_headers(telegram_id)
        params = {"limit": str(limit)}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()
                return data.get("results", data)
        except Exception:
            return []

    async def delete_favorite(self, fav_id: int, *, telegram_id: int) -> bool:
        url = self.base_url + f"favorites/{fav_id}/"
        headers = self._get_auth_headers(telegram_id)

        try:
            async with self.session.delete(url, headers=headers) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    async def create_alert(
        self,
        *,
        telegram_id: int,
        product_id: int,
        threshold_price: float,
        currency: str = "RUB",
        shop_id: int | None = None,
    ) -> bool:
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
                return resp.status in (200, 201)
        except Exception:
            return False

    async def list_alerts(self, *, telegram_id: int, limit: int = DEFAULT_LIMIT):
        url = self.base_url + "price-alerts/"
        headers = self._get_auth_headers(telegram_id)
        params = {"limit": str(limit)}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()
                return data.get("results", data)
        except Exception:
            return []

    async def toggle_alert(self, alert_id: int, *, telegram_id: int) -> bool:
        url = self.base_url + f"price-alerts/{alert_id}/toggle/"
        headers = self._get_auth_headers(telegram_id)

        try:
            async with self.session.post(url, headers=headers) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def delete_alert(self, alert_id: int, *, telegram_id: int) -> bool:
        url = self.base_url + f"price-alerts/{alert_id}/"
        headers = self._get_auth_headers(telegram_id)

        try:
            async with self.session.delete(url, headers=headers) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    async def update_alert_price(
        self, alert_id: int, *, telegram_id: int, threshold_price: float
    ) -> bool:
        url = self.base_url + f"price-alerts/{alert_id}/"
        headers = self._get_auth_headers(telegram_id)
        payload = {"threshold_price": str(threshold_price)}

        try:
            async with self.session.patch(url, json=payload, headers=headers) as resp:
                return resp.status in (200, 202)
        except Exception:
            return False

    async def list_favorites_page(
        self, *, telegram_id: int, limit: int = DEFAULT_OFFERS_LIMIT, offset: int = 0
    ):
        url = self.base_url + "favorites/"
        headers = self._get_auth_headers(telegram_id)
        params = {"limit": str(limit), "offset": str(offset)}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    return [], None, None

                data = await resp.json()
                items = data.get("results", data)
                prev_off = offset - limit if offset > 0 else None
                next_off = offset + limit if data.get("next") else None
                return items, prev_off, next_off
        except Exception:
            return [], None, None

    async def list_alerts_page(
        self, *, telegram_id: int, limit: int = DEFAULT_OFFERS_LIMIT, offset: int = 0
    ):
        url = self.base_url + "price-alerts/"
        headers = self._get_auth_headers(telegram_id)
        params = {"limit": str(limit), "offset": str(offset)}

        try:
            async with self.session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    return [], None, None

                data = await resp.json()
                items = data.get("results", data)
                prev_off = offset - limit if offset > 0 else None
                next_off = offset + limit if data.get("next") else None
                return items, prev_off, next_off
        except Exception:
            return [], None, None

    def _get_auth_headers(self, telegram_id: int) -> dict[str, str]:
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        return headers


async def _safe_text(resp: aiohttp.ClientResponse) -> str:
    try:
        return await resp.text()
    except Exception:
        return "<no text>"
