import asyncio
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin

from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from shared_models import ProductData


class PlaywrightParser:
    def __init__(
        self,
        base_url: str = "https://www.mosigra.ru",
        catalog_path: str = "/nastolnye-igry/",
        max_retries: int = 3,
        retry_delay: int = 2,
    ):
        self.base_url = base_url
        self.catalog_url = f"{base_url}{catalog_path}"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)
        self.failed_urls: List[str] = []
        self.playwright = None

    async def start_browser(self) -> tuple[Browser, Page]:
        """Запуск браузера и создание страницы"""
        self.playwright = await async_playwright().start()
        browser = await self.playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})
        return browser, page

    async def parse_product(self, url: str) -> Optional[ProductData]:
        """Парсинг одного товара"""
        browser, page = await self.start_browser()

        try:
            for attempt in range(self.max_retries):
                try:
                    self.logger.info(f"Парсинг товара (попытка {attempt + 1}): {url}")

                    await page.goto(url, wait_until="networkidle", timeout=15000)
                    await asyncio.sleep(1)

                    # Обрабатываем модальное окно подтверждения возраста
                    await self._handle_age_confirmation(page)

                    # Извлекаем данные товара
                    product_data = await self._extract_product_data(page, url)

                    if product_data:
                        self.logger.info(f"Успешно спаршен товар: {product_data.title}")
                        return product_data

                except PlaywrightTimeoutError:
                    self.logger.warning(
                        f"Таймаут при загрузке {url} (попытка {attempt + 1})"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        self.failed_urls.append(url)
                        return None

                except Exception as e:
                    self.logger.error(
                        f"Ошибка при парсинге {url} (попытка {attempt + 1}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        self.failed_urls.append(url)
                        return None

        finally:
            await browser.close()
            if self.playwright:
                await self.playwright.stop()

        return None

    async def parse_catalog(self, shop_url: str, limit: int = 100) -> List[ProductData]:
        """Парсинг каталога магазина"""
        browser, page = await self.start_browser()
        products = []

        try:
            all_product_links = []

            # Собираем ссылки с нескольких страниц каталога
            for page_num in range(1, 3):  # Максимум 2 страницы
                self.logger.info(f"Обрабатываем страницу каталога {page_num}...")
                links = await self._parse_catalog_page(page, page_num, shop_url)

                if not links:
                    self.logger.info(
                        f"На странице {page_num} товары не найдены, останавливаем"
                    )
                    break

                if links:
                    all_product_links.extend(links)
                self.logger.info(f"Найдено {len(links)} товаров на странице {page_num}")

                if len(all_product_links) >= limit:
                    break

            # Ограничиваем количество товаров
            all_product_links = all_product_links[:limit]
            self.logger.info(f"Всего будет обработано {len(all_product_links)} товаров")

            # Парсим каждый товар
            for i, product_url in enumerate(all_product_links, 1):
                self.logger.info(
                    f"Парсим товар {i}/{len(all_product_links)}: {product_url}"
                )

                product = await self.parse_product(product_url)
                if product:
                    products.append(product)
                    self.logger.info(f"  ✓ {product.title}")
                else:
                    self.logger.error("  ✗ Не удалось спарсить")

                # Небольшая пауза между запросами
                await asyncio.sleep(1)

        finally:
            await browser.close()
            if self.playwright:
                await self.playwright.stop()

        return products

    async def _extract_product_data(
        self, page: Page, url: str
    ) -> Optional[ProductData]:
        """Извлечение данных товара со страницы"""
        try:
            # Извлекаем название
            title_element = await page.query_selector("h1")
            title = await title_element.inner_text() if title_element else ""

            if not title.strip():
                raise ValueError("Не удалось извлечь название товара")

            # Извлекаем цену
            price_rub = await self._extract_price(page)

            # Извлекаем характеристики
            characteristics = await self._extract_characteristics(page)

            # Извлекаем описание
            description = await self._extract_description(page)

            return ProductData(
                title=title.strip(),
                url=url,
                price_rub=price_rub,
                manufacturer=characteristics.get("manufacturer"),
                year=characteristics.get("year"),
                players=characteristics.get("players"),
                play_time=characteristics.get("play_time"),
                age=characteristics.get("age"),
                description=description,
            )

        except Exception as e:
            self.logger.error(f"Ошибка при извлечении данных товара: {e}")
            return None

    async def _extract_price(self, page: Page) -> Optional[int]:
        """Извлечение цены товара"""
        price_selectors = [
            "b.h1",
            ".h1",
            "b[class*='h1']",
            ".price",
            ".product-price",
            "[data-price]",
            ".cost",
            ".amount",
            ".price-current",
            ".current-price",
            ".product-cost",
            ".buy-price",
            ".main-price",
        ]

        for selector in price_selectors:
            price_element = await page.query_selector(selector)
            if price_element:
                price_text = await price_element.inner_text()
                clean_price_text = (
                    price_text.replace(" ", "").replace("\u00a0", "").replace(",", "")
                )

                price_matches = re.findall(r"(\d+)", clean_price_text)
                if price_matches:
                    prices = [
                        int(match) for match in price_matches if int(match) >= 100
                    ]
                    if prices:
                        return max(prices)

        # Дополнительный поиск в контенте страницы
        page_content = await page.content()
        price_matches = re.findall(
            r"(\d{1,2}\s?\d{3}|\d{3,5})\s*(?:₽|руб)", page_content
        )
        if price_matches:
            prices = []
            for match in price_matches:
                try:
                    price_candidate = int(match.replace(" ", ""))
                    if 100 <= price_candidate <= 99999:
                        prices.append(price_candidate)
                except ValueError:
                    continue
            if prices:
                return max(prices)

        return None

    async def _extract_characteristics(self, page: Page) -> dict:
        """Извлечение характеристик товара"""
        characteristics = {}

        char_selectors = [
            "table tr",
            "tbody tr",
            ".characteristics tr",
            ".product-info tr",
            ".specs tr",
            ".properties tr",
            ".details tr",
            ".params tr",
            ".features tr",
            ".info-table tr",
            ".product-table tr",
        ]

        for selector in char_selectors:
            rows = await page.query_selector_all(selector)
            if rows:
                characteristics = await self._process_characteristic_rows(rows)
                if characteristics:
                    break

        return characteristics

    async def _process_characteristic_rows(self, rows) -> dict:
        """Обработка строк характеристик"""
        characteristics = {}

        for row in rows:
            try:
                row_text = await row.inner_text()
                if not row_text.strip():
                    continue

                char_type = self._identify_characteristic_type(row_text)
                if char_type:
                    value = await self._extract_characteristic_value(row)
                    if value:
                        characteristics[char_type] = self._process_characteristic_value(
                            char_type, value
                        )
            except Exception as e:
                self.logger.debug(f"Ошибка при извлечении характеристики: {e}")
                continue

        return characteristics

    def _identify_characteristic_type(self, row_text: str) -> Optional[str]:
        """Определение типа характеристики по тексту строки"""
        row_lower = row_text.lower()

        if any(
            keyword in row_lower
            for keyword in ["производитель", "издатель", "бренд", "компания"]
        ):
            return "manufacturer"
        elif any(keyword in row_lower for keyword in ["год", "дата", "выпуск"]):
            return "year"
        elif "возраст" in row_lower:
            return "age"
        elif (
            any(
                keyword in row_lower
                for keyword in ["количество игрок", "игрок", "участник"]
            )
            and "возраст" not in row_lower
        ):
            return "players"
        elif (
            any(
                keyword in row_lower
                for keyword in ["время", "продолжительность", "длительность", "минут"]
            )
            and "возраст" not in row_lower
        ):
            return "play_time"

        return None

    def _process_characteristic_value(self, char_type: str, value: str) -> any:
        """Обработка значения характеристики"""
        if char_type == "year":
            year_match = re.search(r"(\d{4})", value)
            return int(year_match.group(1)) if year_match else value
        return value

    async def _extract_description(self, page: Page) -> Optional[str]:
        """Извлечение описания товара"""
        desc_selectors = [
            ".description",
            ".product-description",
            ".about",
            ".content",
            ".text",
            ".game-description",
            ".product-text",
            ".info",
            ".overview",
            ".summary",
        ]

        for selector in desc_selectors:
            desc_element = await page.query_selector(selector)
            if desc_element:
                description = await desc_element.inner_text()
                description = description.strip()

                # Очищаем описание от навигации и служебного текста
                description = self._clean_description(description)

                if len(description) > 100 and not description.lower().startswith(
                    "главная"
                ):
                    return description[:600]  # Ограничиваем длину

        return None

    def _clean_description(self, description: str) -> str:
        """Очистка описания от лишнего текста"""
        # Убираем навигационные элементы
        nav_patterns = [
            r"^Главная\s+Каталог.*?(?=\n\n|\w{3,})",
            r"^.*?Каталог.*?Настольные игры.*?(?=\n)",
            r"^.*?Описание\s*Правила.*?(?=\n)",
            r"^\s*\d+-\d+\s*игрок.*?\d+\+\s*",
            r"^Видео\s*",
            r"^Описание\s*",
            r"^Правила\s*",
        ]

        for pattern in nav_patterns:
            description = re.sub(
                pattern, "", description, flags=re.MULTILINE | re.DOTALL
            )

        # Убираем служебные элементы
        cleanup_patterns = [
            r"Наличие и доставка.*?$",
            r"Характеристики.*?$",
            r"Товары серии.*?$",
            r"добавить в корзину",
            r"товар в наличии",
            r"купить",
            r"цена",
            r"скидка",
        ]

        for pattern in cleanup_patterns:
            description = re.sub(
                pattern, "", description, flags=re.IGNORECASE | re.MULTILINE
            )

        # Очищаем лишние пробелы и переносы
        description = re.sub(r"\n\s*\n\s*\n", "\n\n", description)
        description = re.sub(r"^\s*", "", description, flags=re.MULTILINE)

        return description.strip()

    async def _extract_characteristic_value(self, row_element) -> Optional[str]:
        """Извлечение значения характеристики из строки таблицы"""
        try:
            cells = await row_element.query_selector_all("td")
            if len(cells) >= 2:
                value_cell = cells[1]
                link = await value_cell.query_selector("a")
                if link:
                    value = await link.inner_text()
                else:
                    value = await value_cell.inner_text()
                return value.strip() if value else None

            # Если нет td, пробуем разделить по двоеточию
            text = await row_element.inner_text()
            if ":" in text:
                parts = text.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()

        except Exception as e:
            self.logger.debug(f"Ошибка при извлечении значения: {e}")

        return None

    async def _handle_age_confirmation(self, page: Page):
        """Обработка модального окна подтверждения возраста"""
        try:
            age_confirmation_selectors = [
                'button:has-text("Подтвердить")',
                'button:has-text("подтвердить")',
                '.modal-dialog button:has-text("Подтвердить")',
                '.modal-content button:has-text("Подтвердить")',
                'button[data-age="18"]',
                ".age-confirmation button",
                '[data-modal="age"] button',
                'button:has-text("Мне есть 18")',
                'button:has-text("Да, мне есть 18")',
                '.modal button:has-text("18")',
                ".age-modal button",
                ".btn-primary",
                ".btn-confirm",
            ]

            for selector in age_confirmation_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=1000)
                    if button and await button.is_visible():
                        await button.click()
                        await asyncio.sleep(1)
                        return
                except Exception:
                    continue

        except Exception as e:
            self.logger.debug(f"Ошибка при обработке подтверждения возраста: {e}")

    async def _parse_catalog_page(
        self, page: Page, page_num: int = 1, shop_url: str = None
    ) -> List[str]:
        """Парсинг каталожной страницы для получения ссылок на товары"""
        # Используем переданный shop_url вместо self.catalog_url
        catalog_url = shop_url or self.catalog_url
        if page_num > 1:
            catalog_url = f"{catalog_url}?page={page_num}"

        for attempt in range(self.max_retries):
            try:
                self.logger.info(
                    f"Загрузка каталожной страницы {page_num} (попытка {attempt + 1})"
                )
                await page.goto(
                    catalog_url, wait_until="networkidle", timeout=15000
                )
                await asyncio.sleep(2)
                try:
                    await page.wait_for_selector("body", timeout=5000)
                except Exception as e:
                    self.logger.error(f"Страница не загрузилась: {e}")
                    return []

                await self._handle_age_confirmation(page)
                await asyncio.sleep(1)

                links = await self._get_product_links(page, shop_url)
                self.logger.info(f"Найдено {len(links)} товаров на странице {page_num}")
                return links or []

            except PlaywrightTimeoutError:
                self.logger.warning(
                    f"Таймаут при загрузке страницы {catalog_url} "
                    f"(попытка {attempt + 1})"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue

            except Exception as e:
                self.logger.error(
                    f"Ошибка при загрузке страницы {catalog_url} "
                    f"(попытка {attempt + 1}): {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue

        self.logger.error(
            f"Не удалось загрузить страницу {catalog_url} "
            f"после {self.max_retries} попыток"
        )
        return []

    async def _get_product_links(self, page: Page, shop_url: str = None) -> List[str]:
        """Получение ссылок на товары с каталожной страницы"""
        product_links = []

        # Ищем ссылки по URL паттернам
        product_links = await self._find_links_by_patterns(page, shop_url)

        # Если не нашли по URL паттернам, пробуем селекторы
        if not product_links:
            product_links = await self._find_links_by_selectors(page, shop_url)

        return product_links

    async def _find_links_by_patterns(
        self, page: Page, shop_url: str = None
    ) -> List[str]:
        """Поиск ссылок по URL паттернам"""
        product_links = []
        all_links = await page.query_selector_all("a[href]")

        for link in all_links:
            href = await link.get_attribute("href")
            if href and any(
                pattern in href
                for pattern in ["/product/", "/game/", "/nastolnaya-igra-", "/item/"]
            ):
                full_url = urljoin(shop_url or self.base_url, href)
                if full_url not in product_links and self.base_url in full_url:
                    product_links.append(full_url)

        return product_links

    async def _find_links_by_selectors(
        self, page: Page, shop_url: str = None
    ) -> List[str]:
        """Поиск ссылок по CSS селекторам"""
        product_links = []
        selectors = [
            ".product-item a",
            ".catalog-item a",
            ".item a",
            "[data-product-id] a",
            ".product-card a",
            ".card a",
            ".product a",
            ".game a",
            "article a",
            ".listing-item a",
        ]

        for selector in selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                for element in elements:
                    href = await element.get_attribute("href")
                    if href:
                        full_url = urljoin(shop_url or self.base_url, href)
                        if full_url not in product_links and self.base_url in full_url:
                            product_links.append(full_url)
                if product_links:
                    break

        return product_links
