import asyncio
import html
import logging
import re
from typing import Any, List, Optional

from constants import (
    BLACKLIST_SUBSTR,
    DEFAULT_CONCURRENCY,
    DEFAULT_LIMIT,
    DEFAULT_USER_AGENT,
    EXCLUDED_CATEGORIES,
)
from playwright.async_api import Page, async_playwright
from settings import PlaywrightSettings

from shared_models import ProductData

logger = logging.getLogger("parser_results")


# ---------- helpers ----------
def normalize_price(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def normalize_title(raw: str | None) -> str | None:
    if not raw:
        return None
    s = html.unescape(str(raw)).strip()
    m = re.search(r'^\s*Купить\s+[«"“]?(.+?)[»"”]?\s+в\s+Мосигре', s, flags=re.I)
    if m:
        return m.group(1).strip(" \"'«»“”").strip()
    s = re.sub(r"\s+[|–—-]\s*Мосигра.*$", "", s, flags=re.I)
    s = re.sub(r"\s+в\s+Мосигре.*$", "", s, flags=re.I)
    m2 = re.search(r'^\s*Купить\s+[«"“]?(.+?)[»"”]?\s*$', s, flags=re.I)
    if m2:
        s = m2.group(1)
    return s.strip(" \"'«»“”").strip() or None


def pick_attr(attrs: dict, candidates: list) -> str | list | None:
    if not attrs:
        return None
    for k, v in attrs.items():
        key = str(k).strip().lower()
        for c in candidates:
            if isinstance(c, str) and key == c.lower():
                return v
            if hasattr(c, "search") and c.search(key):
                return v
    return None


def normalize_age(value: str | list | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        value = ", ".join([str(x) for x in value if x])
    s = str(value).strip()
    m = re.search(r"(\d+)\s*\+|от\s*(\d+)\s*лет|(\d+)\s*лет", s, flags=re.I)
    if m:
        for grp in m.groups():
            if grp:
                return f"{grp}+"
    return s or None


def absolutize(origin: str, href: str) -> str:
    return origin + href if href.startswith("/") else href


def _norm_players(v):
    if v is None:
        return None
    if isinstance(v, list):
        v = " ".join(str(x) for x in v if x)
    s = str(v).strip().lower().replace("–", "-").replace("—", "-")
    m = re.search(r"от\s*(\d+)\s*до\s*(\d+)", s) or re.search(r"(\d+)\s*-\s*(\d+)", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"(\d+)\s*\+", s)
    if m:
        return f"{m.group(1)}-{m.group(1)}"
    m = re.search(r"\b(\d+)\b", s)
    return m.group(1) if m else None


# ---------- parser ----------
class PlaywrightParser:
    def __init__(self, settings: PlaywrightSettings):
        self.settings = settings

    async def _setup_request_blocking(self, context) -> None:
        async def handler(route, request):
            t = request.resource_type
            u = request.url
            if t in {"image", "media", "font"} or any(
                s in u
                for s in (
                    "google-analytics",
                    "gtag/js",
                    "metrika",
                    "mc.yandex",
                    "doubleclick",
                    "facebook",
                    "vk.com/rtrg",
                    "pixel",
                    "metrics",
                )
            ):
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", handler)

    async def _maybe_close_cookies(self, page: Page) -> None:
        for sel in (
            'button:has-text("Согласен")',
            'button:has-text("Принять")',
            'button:has-text("Ок")',
            'button:has-text("Хорошо")',
            'button:has-text("Понятно")',
            '[data-testid="cookie-accept"]',
            'button[aria-label="Закрыть"]',
        ):
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=500):
                    await loc.click(timeout=500)
                    await page.wait_for_timeout(200)
                    break
            except Exception:
                pass

    async def _maybe_handle_age_gate(self, page: Page) -> None:
        sels = [
            'button:has-text("Подтвердить")',
            'button:has-text("Да, мне есть 18")',
            'button:has-text("Мне есть 18")',
            'button:has-text("Продолжить")',
            '.modal-dialog button:has-text("Подтвердить")',
            '.modal button:has-text("18")',
        ]
        try:
            visible = await page.locator("text=Подтвердите возраст").first.is_visible(
                timeout=800
            )
        except Exception:
            visible = False
        if visible:
            for sel in sels:
                try:
                    loc = page.locator(sel).first
                    if await loc.is_visible(timeout=600):
                        await loc.click(timeout=600)
                        await page.wait_for_timeout(200)
                        break
                except Exception:
                    continue

    async def _auto_scroll(
        self, page: Page, target_count: int, time_budget_ms: int = 10_000
    ) -> None:
        import time

        deadline = time.time() + time_budget_ms / 1000
        prev = -1
        while time.time() < deadline:
            try:
                cnt = await page.locator(
                    "article.card, .card, .product-card, [data-product-id]"
                ).count()
            except Exception:
                cnt = 0
            if cnt >= target_count:
                break
            if cnt == prev:
                await page.wait_for_timeout(300)
                break
            prev = cnt
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_timeout(350)

    async def _get_catalog_links(self, page: Page, limit: int) -> list[str]:
        container_sel = ":is(#productsContainer, .products-container, .products-content, section.category-content)"
        try:
            await page.wait_for_selector(container_sel, timeout=3000)
        except Exception:
            pass

        await self._auto_scroll(page, limit)

        sels = [
            f"{container_sel} article.card a.card__title",
            f"{container_sel} article.card a.card__image",
            f"{container_sel} a.card__title",
            f"{container_sel} a.card__image",
        ]
        logger.info(f"_get_catalog_links: wait container {container_sel}")
        origin = "/".join(page.url.split("/", 3)[:3])
        seen: set[str] = set()
        out: list[str] = []

        for s in sels:
            try:
                batch: list[str] = await page.eval_on_selector_all(
                    s,
                    "els => Array.from(new Set(els.map(e => e.getAttribute('href') || e.href).filter(Boolean)))",
                )
                logger.info(
                    f"_get_catalog_links: selector '{s}' found {len(batch)} links"
                )
            except Exception as e:
                logger.warning(f"_get_catalog_links: selector '{s}' failed: {e}")
                batch = []
            for h in batch:
                full = absolutize(origin, h)
                if any(b in full for b in BLACKLIST_SUBSTR):
                    continue
                if full in seen:
                    continue
                seen.add(full)
                out.append(full)
                if len(out) >= limit:
                    return out[:limit]

        if not out:
            # fallback
            simple = await page.eval_on_selector_all(
                "article.card a.card__title, article.card a.card__image, a.card__title, a.card__image",
                "els => Array.from(new Set(els.map(e => e.getAttribute('href') || e.href).filter(Boolean)))",
            )
            for h in simple:
                full = absolutize(origin, h)
                if any(b in full for b in BLACKLIST_SUBSTR):
                    continue
                if full not in seen:
                    seen.add(full)
                    out.append(full)
                if len(out) >= limit:
                    return out[:limit]
        logger.info(f"_get_catalog_links: collected={len(out)}")
        return out[:limit]

    async def _collect_with_pagination(
        self,
        page: Page,
        limit: int,
        timeout_ms: int,
        page_start: int = 1,
        max_pages: int | None = None,
    ) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()

        async def collect_here():
            nonlocal links
            batch = await self._get_catalog_links(page, limit - len(links))
            for u in batch:
                if u not in seen:
                    seen.add(u)
                    links.append(u)

        # первая страница
        await collect_here()
        if len(links) >= limit:
            return links[:limit]

        # Генерируем URL'ы страниц программно
        base_url = page.url.split("?")[0]  # убираем существующие параметры
        page_urls = []

        for page_num in range(page_start, page_start + (max_pages or 12)):
            generated_url = f"{base_url}?page={page_num}&results_per_page=48"
            page_urls.append(generated_url)

        logger.info(f"Generated {len(page_urls)} page URLs: {page_urls[:5]}")

        # обход страниц
        for u in page_urls:
            if len(links) >= limit:
                break
            try:
                await page.goto(u, wait_until="domcontentloaded", timeout=timeout_ms)
                await self._maybe_handle_age_gate(page)
                await self._maybe_close_cookies(page)
                await collect_here()
            except Exception:
                continue

        return links[:limit]

    # async def _collect_with_pagination(
    #     self,
    #     page: Page,
    #     limit: int,
    #     timeout_ms: int,
    #     page_start: int = 1,
    #     max_pages: int | None = None,
    # ) -> list[str]:
    #     links: list[str] = []
    #     seen: set[str] = set()

    #     async def collect_here():
    #         nonlocal links
    #         batch = await self._get_catalog_links(page, limit - len(links))
    #         for u in batch:
    #             if u not in seen:
    #                 seen.add(u)
    #                 links.append(u)

    #     # первая страница
    #     await collect_here()
    #     if len(links) >= limit:
    #         return links[:limit]

    #     # собрать ссылки пагинации
    #     try:
    #         page_urls: list[str] = await page.eval_on_selector_all(
    #             "ul.pagination a[href*='page=']",
    #             "els => Array.from(new Set(els.map(a => a.href)))",
    #         )
    #         logger.info(
    #             f"_collect_with_pagination: found {len(page_urls)} pagination links: {page_urls[:5]}"
    #         )
    #     except Exception as e:
    #         logger.error(
    #             f"_collect_with_pagination: failed to get pagination links: {e}"
    #         )
    #         page_urls = []

    #     # отсортировать по номеру страницы и выбрать диапазон
    #     def page_num(u: str) -> int:
    #         m = re.search(r"[?&]page=(\d+)", u)
    #         return int(m.group(1)) if m else 1

    #     page_urls = sorted(set(page_urls), key=page_num)
    #     start = page_start - 1  # page_start=1 → start=0, page_start=13 → start=12
    #     end = start + max_pages if max_pages else None
    #     logger.info(f"_collect_with_pagination: page_urls before slice: {len(page_urls)}")
    #     logger.info(f"_collect_with_pagination: start={start}, end={end}, max_pages={max_pages}")
    #     page_urls = page_urls[start:end]
    #     logger.info(f"_collect_with_pagination: page_urls after slice: {len(page_urls)}")

    #     # обход страниц
    #     for u in page_urls:
    #         if len(links) >= limit:
    #             break
    #         try:
    #             await page.goto(u, wait_until="domcontentloaded", timeout=timeout_ms)
    #             await self._maybe_handle_age_gate(page)
    #             await self._maybe_close_cookies(page)
    #             await collect_here()
    #         except Exception:
    #             continue

    #     return links[:limit]

    # async def _collect_with_pagination(
    #     self, page: Page, limit: int, timeout_ms: int
    # ) -> list[str]:
    #     links: list[str] = []
    #     seen: set[str] = set()

    #     async def collect_here():
    #         nonlocal links
    #         batch = await self._get_catalog_links(page, limit - len(links))
    #         for u in batch:
    #             if u not in seen:
    #                 seen.add(u)
    #                 links.append(u)

    #     await collect_here()
    #     logger.info(f"_collect_with_pagination: first_batch={len(links)}")
    #     if len(links) >= limit:
    #         return links[:limit]

    #     try:
    #         page_urls: list[str] = await page.eval_on_selector_all(
    #             "ul.pagination a[href*='page=']",
    #             "els => Array.from(new Set(els.map(a => a.href)))",
    #         )
    #         logger.info(f"_collect_with_pagination: page_urls={len(page_urls)}")
    #     except Exception:
    #         page_urls = []
    #         logger.exception(f"_collect_with_pagination: failed page {page_urls}")

    #     for u in page_urls:
    #         if len(links) >= limit:
    #             break
    #         try:
    #             await page.goto(u, wait_until="domcontentloaded", timeout=timeout_ms)
    #             await self._maybe_handle_age_gate(page)
    #             await self._maybe_close_cookies(page)
    #             await collect_here()
    #         except Exception:
    #             continue
    #     return links[:limit]

    async def _extract_title(self, page: Page) -> Optional[str]:
        try:
            t = await page.eval_on_selector(
                'meta[property="og:title"], meta[name="og:title"]',
                "el => el && (el.getAttribute('content') || el.content)",
            )
            t = normalize_title(t)
            if t:
                return t
        except Exception:
            pass
        for sel in ["h1", ".card_title", ".ProductCard__title", '[itemprop="name"]']:
            try:
                txt = await page.locator(sel).first.text_content(timeout=1000)
                txt = normalize_title(txt)
                if txt:
                    return txt
            except Exception:
                continue
        return None

    async def _extract_price(self, page: Page) -> Optional[int]:
        try:
            price_meta = await page.eval_on_selector(
                'meta[itemprop="price"]',
                "el => el && (el.getAttribute('content') || el.content)",
            )
            p = normalize_price(price_meta)
            if p:
                return p
        except Exception:
            pass
        try:
            price_item = await page.eval_on_selector(
                '[itemprop="price"]',
                "el => el && ((el.getAttribute('content') || el.content) || el.textContent)",
            )
            p = normalize_price(price_item)
            if p:
                return p
        except Exception:
            pass
        for sel in (
            "b.h1",
            ".h1",
            ".price",
            ".price__current",
            ".ProductCard__price-current",
            ".product-price",
            ".amount",
            ".cost",
            ".buy-price",
            ".main-price",
        ):
            try:
                txt = await page.locator(sel).first.text_content(timeout=800)
                p = normalize_price(txt)
                if p:
                    return p
            except Exception:
                continue
        return None

    async def _extract_attributes(self, page: Page) -> dict[str, Any]:
        try:
            return await page.evaluate("""
() => {
  const out = {};
  const sect = document.querySelector('section#attributes');
  const table = sect ? sect.querySelector('table') : document.querySelector('#attributes table');
  if (!table) return out;
  const rows = Array.from(table.querySelectorAll('tr'));
  for (const tr of rows) {
    const tds = tr.querySelectorAll('td');
    if (tds.length < 2) continue;
    const k = tds[0].textContent?.trim() || '';
    const td2 = tds[1];
    let v = td2.textContent?.trim() || '';
    const links = Array.from(td2.querySelectorAll('a')).map(a => a.textContent?.trim()).filter(Boolean);
    out[k] = links.length ? links : v;
  }
  return out;
}
""")
        except Exception:
            return {}

    async def _extract_categories(self, page: Page) -> list[str]:
        try:
            cats = await page.eval_on_selector_all(
                "article.categories a.categories_link, .categories a.categories_link, a.categories_link",
                "els => els.map(e => e.textContent && e.textContent.trim()).filter(Boolean)",
            )
            if not cats:
                cats = await page.eval_on_selector_all(
                    ".categories a, .breadcrumbs a, .breadcrumb a",
                    "els => els.map(e => e.textContent && e.textContent.trim()).filter(Boolean)",
                )
        except Exception:
            cats = []
        result, seen = [], set()
        for c in cats or []:
            if c in EXCLUDED_CATEGORIES:
                continue
            if c in seen:
                continue
            seen.add(c)
            result.append(c)
        return result

    # ---------- public API ----------
    async def parse_product(self, url: str) -> Optional[ProductData]:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.settings.headless)
            context = await browser.new_context(
                user_agent=DEFAULT_USER_AGENT,
                viewport=self.settings.viewport_size,
                locale="ru-RU",
            )
            await self._setup_request_blocking(context)
            page = await context.new_page()
            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.timeout * 1000,
                )
                logger.info(f"parse_product: {url}")
                await self._maybe_handle_age_gate(page)
                await self._maybe_close_cookies(page)
                try:
                    await page.wait_for_selector(
                        "main, h1, .card_title, .ProductCard__title", timeout=2500
                    )
                except Exception:
                    pass

                title = await self._extract_title(page)
                if not title:
                    logger.warning(f"parse_product: no title for {url}")
                    return None
                price = await self._extract_price(page)
                attrs = await self._extract_attributes(page)
                categories = await self._extract_categories(page)

                manufacturers: list[str] = []
                prod_raw = pick_attr(
                    attrs, ["Производитель", re.compile(r"производител", re.I)]
                )
                if isinstance(prod_raw, list):
                    manufacturers = [s for s in prod_raw if s]
                elif isinstance(prod_raw, str) and prod_raw.strip():
                    manufacturers = [
                        s.strip() for s in prod_raw.split(",") if s.strip()
                    ]

                def _pick_players(attrs: dict) -> str | list | None:
                    for k, v in attrs.items():
                        key = str(k).strip().lower()
                        if "возраст" in key:  # игнорируем "Возраст игроков"
                            continue
                        if key in (
                            "количество игроков",
                            "игроков",
                            "число игроков",
                        ) or re.search(r"\bигрок", key):
                            return v
                    return None

                players = _pick_players(attrs)
                players_norm = _norm_players(players)
                play_time = pick_attr(
                    attrs,
                    [
                        "Время игры",
                        "Продолжительность игры",
                        re.compile(r"время.*игр", re.I),
                    ],
                )
                age = normalize_age(
                    pick_attr(
                        attrs,
                        [
                            "Возраст игроков",
                            "Возраст",
                            "Возраст игрока",
                            "Возрастные ограничения",
                            re.compile(r"возраст", re.I),
                        ],
                    )
                )

                return ProductData(
                    title=title,
                    url=url,
                    price_rub=price,
                    manufacturers=manufacturers,
                    categories=categories,
                    players=players_norm,
                    play_time=str(play_time).strip() if play_time else None,
                    age=age,
                )
            finally:
                await context.close()
                await browser.close()

    # async def parse_catalog(
    #     self, shop_url: str, limit: int = DEFAULT_LIMIT
    # ) -> List[ProductData]:
    #     async with async_playwright() as pw:
    #         browser = await pw.chromium.launch(headless=self.settings.headless)
    #         context = await browser.new_context(
    #             user_agent=DEFAULT_USER_AGENT,
    #             viewport=self.settings.viewport_size,
    #             locale="ru-RU",
    #         )
    #         await self._setup_request_blocking(context)
    #         page = await context.new_page()
    #         try:
    #             await page.goto(
    #                 shop_url,
    #                 wait_until="domcontentloaded",
    #                 timeout=self.settings.timeout * 1000,
    #             )
    #             logger.info(
    #                 f"parse_catalog: url={shop_url}, headless={self.settings.headless}, timeout={self.settings.timeout}s"
    #             )
    #             await self._maybe_handle_age_gate(page)
    #             await self._maybe_close_cookies(page)
    #             links = await self._collect_with_pagination(
    #                 page, limit, self.settings.timeout * 1000
    #             )
    #             logger.info(f"parse_catalog: links={len(links)}")
    #             if not links:
    #                 return []

    #             sem = asyncio.Semaphore(DEFAULT_CONCURRENCY)

    #             async def worker(u: str):
    #                 async with sem:
    #                     p = await context.new_page()
    #                     try:
    #                         return await self.parse_product(u)
    #                     finally:
    #                         await p.close()

    #             results = await asyncio.gather(*(worker(u) for u in links))
    #             ok = [r for r in results if r]
    #             logger.info(f"parse_catalog: parsed={len(ok)}")
    #             return ok
    #         finally:
    #             await context.close()
    #             await browser.close()

    async def parse_catalog(
        self,
        shop_url: str,
        limit: int = DEFAULT_LIMIT,
        page_start: int = 1,
        max_pages: int | None = None,
    ) -> List[ProductData]:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.settings.headless)
            context = await browser.new_context(
                user_agent=DEFAULT_USER_AGENT,
                viewport=self.settings.viewport_size,
                locale="ru-RU",
            )
            await self._setup_request_blocking(context)
            page = await context.new_page()
            try:
                await page.goto(
                    shop_url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.timeout * 1000,
                )
                logger.info(
                    f"parse_catalog: url={shop_url}, headless={self.settings.headless}, timeout={self.settings.timeout}s"
                )
                await self._maybe_handle_age_gate(page)
                await self._maybe_close_cookies(page)
                links = await self._collect_with_pagination(
                    page,
                    limit,
                    self.settings.timeout * 1000,
                    page_start=page_start,
                    max_pages=max_pages,
                )
                logger.info(f"parse_catalog: links={len(links)}")
                if not links:
                    return []

                sem = asyncio.Semaphore(DEFAULT_CONCURRENCY)

                async def worker(u: str):
                    async with sem:
                        p = await context.new_page()
                        try:
                            return await self.parse_product(u)
                        except Exception as e:
                            logger.warning(f"Failed to parse product {u}: {e}")
                            return None  # Возвращаем None вместо падения
                        finally:
                            await p.close()

                results = await asyncio.gather(*(worker(u) for u in links))
                ok = [r for r in results if r]
                logger.info(f"parse_catalog: parsed={len(ok)}")
                return ok
            finally:
                await context.close()
                await browser.close()
