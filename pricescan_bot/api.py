import logging
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class ApiClient:
    def __init__(self, base_url: str, service_token: str):
        self.base_url = base_url.rstrip("/") + "/"
        self.service_token = service_token
        self._session: Optional[aiohttp.ClientSession] = None
        self._access_by_tg: dict[int, str] = {}

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
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
        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                await _safe_text(resp)
                logger.warning("JWT fetch failed: %s", resp.status)
                return None
            data = await resp.json()
            access = data.get("access")
            if access:
                self._access_by_tg[telegram_id] = access
            return access

    async def get_cheapest(self, query: str) -> Optional[Dict[str, Any]]:
        url = self.base_url + "products/cheapest/"
        params = {"q": query}
        async with self.session.get(url, params=params) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

    async def get_offers(self, product_id: int, limit: int = 5):
        url = self.base_url + "offers/"
        params = {
            "product": str(product_id),
            "is_available": "true",
            "ordering": "price",
            "limit": str(limit),
        }
        async with self.session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            items = data.get("results", data)
            return list(items)[:limit]

    async def add_search_history(
        self, *, telegram_id: int, query: str, results_count: int
    ) -> bool:
        url = self.base_url + "search-history/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        payload = {"query": query, "results_count": int(results_count)}
        async with self.session.post(url, json=payload, headers=headers) as resp:
            return resp.status in (200, 201)

    async def get_search_history(self, *, telegram_id: int, limit: int = 10):
        url = self.base_url + "search-history/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        params = {"limit": str(limit)}
        async with self.session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("results", data)

    async def clear_search_history(self, *, telegram_id: int) -> bool:
        url = self.base_url + "search-history/clear/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        async with self.session.delete(url, headers=headers) as resp:
            return resp.status == 200

    async def refresh_product(
        self, product_id: int, *, telegram_id: Optional[int] = None
    ) -> bool:
        url = self.base_url + f"products/{product_id}/refresh/"
        headers = {}
        if telegram_id is not None and telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        async with self.session.post(url, headers=headers) as resp:
            return resp.status == 202

    # Избранное
    async def add_favorite(self, product_id: int, *, telegram_id: int) -> bool:
        url = self.base_url + "favorites/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        payload = {"product": int(product_id)}
        async with self.session.post(url, json=payload, headers=headers) as resp:
            return resp.status in (200, 201)

    async def list_favorites(self, *, telegram_id: int, limit: int = 10):
        url = self.base_url + "favorites/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        params = {"limit": str(limit)}
        async with self.session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("results", data)

    async def delete_favorite(self, fav_id: int, *, telegram_id: int) -> bool:
        url = self.base_url + f"favorites/{fav_id}/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        async with self.session.delete(url, headers=headers) as resp:
            return resp.status in (200, 204)

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
        url = self.base_url + "price-alerts/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        payload = {
            "product": product_id,
            "threshold_price": str(threshold_price),
            "currency": currency,
        }
        if shop_id:
            payload["shop"] = shop_id
        async with self.session.post(url, json=payload, headers=headers) as resp:
            return resp.status in (200, 201)

    async def list_alerts(self, *, telegram_id: int, limit: int = 10):
        url = self.base_url + "price-alerts/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        params = {"limit": str(limit)}
        async with self.session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("results", data)

    async def toggle_alert(self, alert_id: int, *, telegram_id: int) -> bool:
        url = self.base_url + f"price-alerts/{alert_id}/toggle/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        async with self.session.post(url, headers=headers) as resp:
            return resp.status == 200

    async def delete_alert(self, alert_id: int, *, telegram_id: int) -> bool:
        url = self.base_url + f"price-alerts/{alert_id}/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        async with self.session.delete(url, headers=headers) as resp:
            return resp.status in (200, 204)

    async def update_alert_price(
        self, alert_id: int, *, telegram_id: int, threshold_price: float
    ) -> bool:
        """Изменить пороговую цену у алёрта."""
        url = self.base_url + f"price-alerts/{alert_id}/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        payload = {"threshold_price": str(threshold_price)}
        async with self.session.patch(url, json=payload, headers=headers) as resp:
            return resp.status in (200, 202)

    async def list_favorites_page(
        self, *, telegram_id: int, limit: int = 5, offset: int = 0
    ):
        url = self.base_url + "favorites/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        params = {"limit": str(limit), "offset": str(offset)}
        async with self.session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                return [], None, None
            data = await resp.json()
            items = data.get("results", data)
            prev_off = offset - limit if offset > 0 else None
            next_off = offset + limit if data.get("next") else None
            return items, prev_off, next_off

    async def list_alerts_page(
        self, *, telegram_id: int, limit: int = 5, offset: int = 0
    ):
        url = self.base_url + "price-alerts/"
        headers = {}
        if telegram_id in self._access_by_tg:
            headers["Authorization"] = f"Bearer {self._access_by_tg[telegram_id]}"
        params = {"limit": str(limit), "offset": str(offset)}
        async with self.session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                return [], None, None
            data = await resp.json()
            items = data.get("results", data)
            prev_off = offset - limit if offset > 0 else None
            next_off = offset + limit if data.get("next") else None
            return items, prev_off, next_off


async def _safe_text(resp: aiohttp.ClientResponse) -> str:
    try:
        return await resp.text()
    except Exception:
        return "<no text>"
