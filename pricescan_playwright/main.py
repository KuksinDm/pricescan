import asyncio
import json
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin

from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Показываем debug сообщения в консоли
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("parser.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


class Product(BaseModel):
    title: str
    url: str
    price_rub: Optional[int] = None
    manufacturer: Optional[str] = None  # производитель
    year: Optional[int] = None  # год выпуска
    players: Optional[str] = None  # количество игроков "1-2"
    play_time: Optional[str] = None  # время партии "60-120"
    age: Optional[str] = None  # возраст "14+"
    description: Optional[str] = None


class MosigraParser:
    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        self.base_url = "https://www.mosigra.ru"
        self.catalog_url = "https://www.mosigra.ru/nastolnye-igry/"
        self.products: List[Product] = []
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)
        self.failed_urls: List[str] = []
        self.playwright = None

    async def start_browser(self) -> tuple[Browser, Page]:
        """Запуск браузера и создание страницы"""
        self.playwright = await async_playwright().start()
        browser = await self.playwright.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})
        return browser, page

    async def parse_product_card(
        self, page: Page, product_url: str
    ) -> Optional[Product]:
        """Парсинг отдельной карточки товара с retry логикой"""
        for attempt in range(self.max_retries):
            try:
                self.logger.info(
                    f"Парсинг товара (попытка {attempt + 1}): {product_url}"
                )

                # Переход на страницу товара с таймаутом
                await page.goto(
                    product_url, wait_until="domcontentloaded", timeout=15000
                )
                await asyncio.sleep(1)  # Дополнительное время для загрузки

                # Проверяем и обрабатываем модальное окно подтверждения возраста (18+)
                await self._handle_age_confirmation(page)

                # Извлекаем название
                title_element = await page.query_selector("h1")
                title = await title_element.inner_text() if title_element else ""

                if not title.strip():
                    raise ValueError("Не удалось извлечь название товара")

                # Извлекаем цену
                price_rub = None
                price_selectors = [
                    "b.h1",  # Основная цена как на скриншоте
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
                        # Очищаем от всех видов пробелов включая &nbsp;
                        clean_price_text = (
                            price_text.replace(" ", "")
                            .replace("\u00a0", "")
                            .replace(",", "")
                        )

                        # Ищем числа (могут быть с рублями или без)
                        price_matches = re.findall(r"(\d+)", clean_price_text)
                        if price_matches:
                            # Берем наибольшее число (обычно это цена)
                            prices = [
                                int(match)
                                for match in price_matches
                                if int(match) >= 100
                            ]
                            if prices:
                                price_rub = max(prices)
                                self.logger.debug(
                                    f"Найдена цена: {price_rub} руб. (селектор: {selector}, текст: '{price_text.strip()}')"
                                )
                                break

                # Если не нашли цену по селекторам, ищем в тексте страницы
                if price_rub is None:
                    page_content = await page.content()
                    # Ищем числа от 100 до 99999 с пробелами (российский формат цен)
                    price_matches = re.findall(
                        r"(\d{1,2}\s?\d{3}|\d{3,5})\s*(?:₽|руб)", page_content
                    )
                    if price_matches:
                        # Собираем все найденные цены и выбираем наибольшую разумную
                        prices = []
                        for match in price_matches:
                            try:
                                price_candidate = int(match.replace(" ", ""))
                                if 100 <= price_candidate <= 99999:  # Разумный диапазон
                                    prices.append(price_candidate)
                            except ValueError:
                                continue

                        if prices:
                            # Берем наибольшую цену (обычно это основная цена товара)
                            price_rub = max(prices)
                            self.logger.debug(
                                f"Найдена цена в контенте: {price_rub} руб."
                            )

                # Дополнительная попытка - ищем в элементах с ценами
                if price_rub is None:
                    price_containers = await page.query_selector_all(
                        '[class*="price"], [class*="cost"], [class*="buy"]'
                    )
                    for container in price_containers:
                        try:
                            text = await container.inner_text()
                            # Ищем крупные числа с пробелами
                            price_match = re.search(
                                r"(\d{1,2}\s?\d{3}|\d{3,5})\s*(?:₽|руб)", text
                            )
                            if price_match:
                                price_candidate = int(
                                    price_match.group(1).replace(" ", "")
                                )
                                if 100 <= price_candidate <= 99999:
                                    price_rub = price_candidate
                                    self.logger.debug(
                                        f"Найдена цена в контейнере: {price_rub} руб."
                                    )
                                    break
                        except:
                            continue

                # Извлекаем характеристики из таблицы или списка
                manufacturer = None
                year = None
                players = None
                play_time = None
                age = None
                description = None

                # Сначала получаем весь текст страницы для поиска характеристик
                page_text = await page.inner_text("body")

                # Ищем характеристики в различных возможных селекторах
                char_selectors = [
                    "table tr",  # Общий селектор для всех таблиц
                    "tbody tr",  # Строки в теле таблицы
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
                    characteristics = await page.query_selector_all(selector)
                    if characteristics:
                        self.logger.debug(
                            f"Найдены характеристики по селектору {selector}: {len(characteristics)} строк"
                        )
                        for row in characteristics:
                            try:
                                row_text = await row.inner_text()
                                if not row_text.strip():
                                    continue

                                self.logger.debug(
                                    f"Обрабатываем строку: {row_text.strip()}"
                                )

                                # Производитель/издатель
                                if any(
                                    keyword in row_text.lower()
                                    for keyword in [
                                        "производитель",
                                        "издатель",
                                        "бренд",
                                        "компания",
                                    ]
                                ):
                                    manufacturer = (
                                        await self._extract_characteristic_value(row)
                                    )
                                    if manufacturer:
                                        self.logger.debug(
                                            f"Найден производитель: {manufacturer}"
                                        )

                                # Год выпуска
                                elif any(
                                    keyword in row_text.lower()
                                    for keyword in ["год", "дата", "выпуск"]
                                ):
                                    year_text = (
                                        await self._extract_characteristic_value(row)
                                    )
                                    if year_text:
                                        year_match = re.search(r"(\d{4})", year_text)
                                        if year_match:
                                            year = int(year_match.group(1))
                                            self.logger.debug(f"Найден год: {year}")

                                # Возраст игроков (ищем строки с "возраст")
                                if "возраст" in row_text.lower():
                                    age = await self._extract_characteristic_value(row)
                                    if age:
                                        self.logger.debug(f"Найден возраст: {age}")

                                # Количество игроков (ищем строки с "количество игрок" или просто "игрок", но БЕЗ "возраст")
                                elif (
                                    any(
                                        keyword in row_text.lower()
                                        for keyword in [
                                            "количество игрок",
                                            "игрок",
                                            "участник",
                                        ]
                                    )
                                    and "возраст" not in row_text.lower()
                                ):
                                    players = await self._extract_characteristic_value(
                                        row
                                    )
                                    if players:
                                        self.logger.debug(f"Найдено игроков: {players}")

                                # Время игры
                                elif (
                                    any(
                                        keyword in row_text.lower()
                                        for keyword in [
                                            "время",
                                            "продолжительность",
                                            "длительность",
                                            "минут",
                                        ]
                                    )
                                    and "возраст" not in row_text.lower()
                                ):
                                    play_time = (
                                        await self._extract_characteristic_value(row)
                                    )
                                    if play_time:
                                        self.logger.debug(
                                            f"Найдено время игры: {play_time}"
                                        )

                            except Exception as e:
                                self.logger.debug(
                                    f"Ошибка при извлечении характеристики: {e}"
                                )
                                continue

                        # Если нашли хотя бы одну характеристику, прекращаем поиск
                        if any([manufacturer, year, players, play_time, age]):
                            break

                # Если не нашли в таблицах, пробуем извлечь из текста страницы
                if not any([players, play_time, age]):
                    # Ищем паттерны в тексте страницы

                    # Количество игроков
                    if not players:
                        players_patterns = [
                            r"(\d+[-–—]\d+)\s*игрок",
                            r"(\d+[-–—]\d+)\s*участник",
                            r"(\d+)\s*[-–—]\s*(\d+)\s*игрок",
                            r"для\s*(\d+[-–—]\d+)\s*игрок",
                        ]
                        for pattern in players_patterns:
                            match = re.search(pattern, page_text, re.IGNORECASE)
                            if match:
                                if (
                                    "-" in match.group(1)
                                    or "–" in match.group(1)
                                    or "—" in match.group(1)
                                ):
                                    players = match.group(1)
                                else:
                                    players = f"{match.group(1)}-{match.group(2)}"
                                self.logger.debug(
                                    f"Найдено игроков из текста: {players}"
                                )
                                break

                    # Время игры
                    if not play_time:
                        time_patterns = [
                            r"(\d+[-–—]\d+)\s*минут",
                            r"(\d+)\s*[-–—]\s*(\d+)\s*минут",
                            r"(\d+\+?)\s*минут",
                        ]
                        for pattern in time_patterns:
                            match = re.search(pattern, page_text, re.IGNORECASE)
                            if match:
                                if len(match.groups()) > 1 and match.group(2):
                                    play_time = (
                                        f"{match.group(1)}-{match.group(2)} минут"
                                    )
                                else:
                                    play_time = match.group(1) + " минут"
                                self.logger.debug(
                                    f"Найдено время игры из текста: {play_time}"
                                )
                                break

                    # Возраст
                    if not age:
                        age_patterns = [
                            r"(\d+)\+",
                            r"от\s*(\d+)\s*лет",
                            r"(\d+)\s*лет\s*\+",
                        ]
                        for pattern in age_patterns:
                            match = re.search(pattern, page_text, re.IGNORECASE)
                            if match:
                                age = match.group(1) + "+"
                                self.logger.debug(f"Найден возраст из текста: {age}")
                                break

                # Извлекаем описание
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
                        description = description.strip()

                        # Убираем навигационные элементы в начале
                        nav_patterns = [
                            r"^Главная\s+Каталог.*?(?=\n\n|\w{3,})",
                            r"^.*?Каталог.*?Настольные игры.*?(?=\n)",
                            r"^.*?Описание\s*Правила.*?(?=\n)",
                            r"^\s*\d+-\d+\s*игрок.*?\d+\+\s*",
                            r"^Видео\s*",  # Убираем "Видео" в начале
                            r"^Описание\s*",  # Убираем "Описание" в начале
                            r"^Правила\s*",  # Убираем "Правила" в начале
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
                            r"^Видео\n",  # Убираем "Видео" с переносом строки
                            r"^Описание\n",  # Убираем "Описание" с переносом строки
                            r"^Правила\n",  # Убираем "Правила" с переносом строки
                            r"^ХИТ\s*\n",  # Убираем "ХИТ"
                            r"^\d+\+\s*\n",  # Убираем возрастные ограничения в начале
                        ]

                        for pattern in cleanup_patterns:
                            description = re.sub(
                                pattern,
                                "",
                                description,
                                flags=re.IGNORECASE | re.MULTILINE,
                            )

                        # Очищаем лишние пробелы и переносы
                        description = re.sub(r"\n\s*\n\s*\n", "\n\n", description)
                        description = re.sub(
                            r"^\s*", "", description, flags=re.MULTILINE
                        )
                        description = description.strip()

                        # Проверяем качество описания
                        if (
                            len(description) > 100
                            and not description.lower().startswith("главная")
                            and "каталог" not in description.lower()[:50]
                        ):
                            description = description[:600]  # Ограничиваем длину
                            self.logger.debug(
                                f"Найдено очищенное описание: {description[:100]}..."
                            )
                            break
                        else:
                            description = None

                product = Product(
                    title=title.strip(),
                    url=product_url,
                    price_rub=price_rub,
                    manufacturer=manufacturer,
                    year=year,
                    players=players,
                    play_time=play_time,
                    age=age,
                    description=description,
                )

                self.logger.info(f"Успешно спаршен товар: {title.strip()}")
                return product

            except PlaywrightTimeoutError:
                self.logger.warning(
                    f"Таймаут при загрузке {product_url} (попытка {attempt + 1})"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    self.failed_urls.append(product_url)
                    return None

            except Exception as e:
                self.logger.error(
                    f"Ошибка при парсинге {product_url} (попытка {attempt + 1}): {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    self.failed_urls.append(product_url)
                    return None

        return None

    async def _handle_age_confirmation(self, page: Page):
        """Обработка модального окна подтверждения возраста для игр 18+"""
        try:
            # Различные возможные селекторы для кнопки подтверждения возраста
            age_confirmation_selectors = [
                'button:has-text("Подтвердить")',  # Основная кнопка с скриншота
                'button:has-text("подтвердить")',  # В нижнем регистре
                '.modal-dialog button:has-text("Подтвердить")',
                '.modal-content button:has-text("Подтвердить")',
                'button[data-age="18"]',
                ".age-confirmation button",
                '[data-modal="age"] button',
                'button:has-text("Мне есть 18")',
                'button:has-text("Да, мне есть 18")',
                '.modal button:has-text("18")',
                ".age-modal button",
                '[data-dismiss="modal"]:has-text("18")',
                'button:has-text("Продолжить")',
                # Добавляем селекторы по классам
                ".btn-primary",
                ".btn-confirm",
                ".confirm-button",
            ]

            # Ждем появления модального окна (максимум 3 секунды)
            for selector in age_confirmation_selectors:
                try:
                    # Проверяем, есть ли кнопка подтверждения возраста
                    button = await page.wait_for_selector(selector, timeout=1000)
                    if button:
                        # Проверяем, видима ли кнопка
                        is_visible = await button.is_visible()
                        if is_visible:
                            self.logger.info(
                                f"Найдена кнопка подтверждения возраста: {selector}"
                            )
                            await button.click()
                            await asyncio.sleep(1)  # Ждем закрытия модального окна
                            self.logger.info("Подтверждение возраста выполнено")
                            return
                except:
                    continue

            # Дополнительная проверка через текст всех кнопок
            try:
                buttons = await page.query_selector_all("button")
                self.logger.debug(f"Найдено {len(buttons)} кнопок на странице")

                for button in buttons:
                    try:
                        text = await button.inner_text()
                        if text:
                            text_lower = text.strip().lower()
                            self.logger.debug(
                                f"Проверяем кнопку с текстом: '{text.strip()}'"
                            )

                            # Ищем кнопки с ключевыми словами
                            if any(
                                keyword in text_lower
                                for keyword in [
                                    "подтвердить",
                                    "подтверждаю",
                                    "подтверждение",
                                    "да",
                                    "согласен",
                                    "принимаю",
                                    "ок",
                                    "продолжить",
                                    "18",
                                    "взрослый",
                                    "совершеннолетний",
                                ]
                            ):
                                is_visible = await button.is_visible()
                                if is_visible:
                                    self.logger.info(
                                        f"Найдена кнопка подтверждения по тексту: '{text.strip()}'"
                                    )
                                    await button.click()
                                    await asyncio.sleep(2)  # Увеличиваем время ожидания
                                    self.logger.info("Подтверждение возраста выполнено")
                                    return
                    except Exception as e:
                        self.logger.debug(f"Ошибка при проверке кнопки: {e}")
                        continue
            except Exception as e:
                self.logger.debug(f"Ошибка при поиске кнопок: {e}")

            # Последняя попытка - ищем модальное окно и кликаем первую видимую кнопку в нем
            try:
                modal_selectors = [
                    ".modal",
                    ".modal-dialog",
                    ".modal-content",
                    ".popup",
                    ".overlay",
                ]
                for modal_selector in modal_selectors:
                    modal = await page.query_selector(modal_selector)
                    if modal:
                        is_visible = await modal.is_visible()
                        if is_visible:
                            # Ищем кнопки внутри модального окна
                            modal_buttons = await modal.query_selector_all("button")
                            for button in modal_buttons:
                                try:
                                    text = await button.inner_text()
                                    if text and "подтвердить" in text.lower():
                                        self.logger.info(
                                            f"Найдена кнопка в модальном окне: '{text.strip()}'"
                                        )
                                        await button.click()
                                        await asyncio.sleep(2)
                                        self.logger.info(
                                            "Подтверждение возраста выполнено через модальное окно"
                                        )
                                        return
                                except:
                                    continue
            except Exception as e:
                self.logger.debug(f"Ошибка при поиске модального окна: {e}")

        except Exception as e:
            self.logger.debug(f"Ошибка при обработке подтверждения возраста: {e}")

    async def _extract_characteristic_value(self, row_element) -> Optional[str]:
        """Извлечение значения характеристики из строки таблицы"""
        try:
            # Ищем ячейки таблицы
            cells = await row_element.query_selector_all("td")
            if len(cells) >= 2:
                # Берем вторую ячейку (значение)
                value_cell = cells[1]

                # Проверяем, есть ли ссылка внутри ячейки
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
            self.logger.debug(f"Ошибка при извлечении значения из строки таблицы: {e}")

        return None

    async def get_product_links(self, page: Page) -> List[str]:
        """Получение ссылок на товары с каталожной страницы"""
        product_links = []

        # Сначала попробуем найти все ссылки на товары
        all_links = await page.query_selector_all("a[href]")

        for link in all_links:
            href = await link.get_attribute("href")
            if href:
                # Фильтруем ссылки, которые похожи на товары
                if any(
                    pattern in href
                    for pattern in [
                        "/product/",
                        "/game/",
                        "/nastolnaya-igra-",
                        "/item/",
                    ]
                ):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in product_links and self.base_url in full_url:
                        product_links.append(full_url)

        # Если не нашли по URL паттернам, попробуем различные селекторы
        if not product_links:
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
                    self.logger.info(f"Найдены элементы по селектору: {selector}")
                    for element in elements:
                        href = await element.get_attribute("href")
                        if href:
                            full_url = urljoin(self.base_url, href)
                            if (
                                full_url not in product_links
                                and self.base_url in full_url
                            ):
                                product_links.append(full_url)
                    if product_links:  # Если нашли товары, прекращаем поиск
                        break

        self.logger.info(f"Найдено {len(product_links)} ссылок на товары")
        return product_links

    async def debug_page_structure(self, page: Page):
        """Отладочная функция для анализа структуры страницы"""
        try:
            # Получаем заголовок страницы
            title = await page.title()
            self.logger.info(f"Заголовок страницы: {title}")

            # Ищем различные контейнеры товаров
            containers = [
                ".products",
                ".catalog",
                ".items",
                ".cards",
                ".product-list",
                ".game-list",
                "[data-products]",
            ]

            for container in containers:
                elements = await page.query_selector_all(container)
                if elements:
                    self.logger.info(
                        f"Найден контейнер товаров: {container} ({len(elements)} элементов)"
                    )

            # Проверяем общее количество ссылок
            all_links = await page.query_selector_all("a")
            self.logger.info(f"Всего ссылок на странице: {len(all_links)}")

            # Ищем ссылки с текстом, содержащим игры
            game_links = []
            for link in all_links[:20]:  # Проверяем первые 20 ссылок
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute("href")
                    if text and href and len(text.strip()) > 3:
                        game_links.append(f"{text.strip()[:50]} -> {href}")
                except:
                    continue

            if game_links:
                self.logger.info("Примеры ссылок на странице:")
                for link_info in game_links[:5]:
                    self.logger.info(f"  {link_info}")

        except Exception as e:
            self.logger.error(f"Ошибка при отладке структуры страницы: {e}")

    async def parse_catalog_page(self, page: Page, page_num: int = 1) -> List[str]:
        """Парсинг каталожной страницы для получения ссылок на товары с retry логикой"""
        catalog_url = (
            f"{self.catalog_url}?page={page_num}" if page_num > 1 else self.catalog_url
        )

        for attempt in range(self.max_retries):
            try:
                self.logger.info(
                    f"Загрузка каталожной страницы {page_num} (попытка {attempt + 1})"
                )
                await page.goto(
                    catalog_url, wait_until="domcontentloaded", timeout=15000
                )
                await asyncio.sleep(2)  # Даем время загрузиться

                # Проверяем и обрабатываем модальное окно подтверждения возраста
                await self._handle_age_confirmation(page)
                await asyncio.sleep(1)  # Дополнительное время после подтверждения

                # Добавляем отладку для первой страницы
                if page_num == 1:
                    await self.debug_page_structure(page)

                links = await self.get_product_links(page)
                self.logger.info(f"Найдено {len(links)} товаров на странице {page_num}")

                # Выводим первые несколько ссылок для отладки
                if links:
                    self.logger.info("Примеры найденных ссылок:")
                    for link in links[:3]:
                        self.logger.info(f"  {link}")

                return links

            except PlaywrightTimeoutError:
                self.logger.warning(
                    f"Таймаут при загрузке страницы {catalog_url} (попытка {attempt + 1})"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue

            except Exception as e:
                self.logger.error(
                    f"Ошибка при загрузке страницы {catalog_url} (попытка {attempt + 1}): {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue

        self.logger.error(
            f"Не удалось загрузить страницу {catalog_url} после {self.max_retries} попыток"
        )
        return []

    async def run(self, max_pages: int = 5, max_products: int = 50):
        """Основной метод запуска парсера"""
        browser, page = await self.start_browser()

        try:
            print("Начинаем парсинг mosigra.ru...")

            all_product_links = []

            # Собираем ссылки с нескольких страниц каталога
            for page_num in range(1, max_pages + 1):
                print(f"Обрабатываем страницу каталога {page_num}...")
                links = await self.parse_catalog_page(page, page_num)

                if not links:
                    print(f"На странице {page_num} товары не найдены, останавливаем")
                    break

                all_product_links.extend(links)
                print(f"Найдено {len(links)} товаров на странице {page_num}")

                if len(all_product_links) >= max_products:
                    break

            # Ограничиваем количество товаров
            all_product_links = all_product_links[:max_products]
            print(f"Всего будет обработано {len(all_product_links)} товаров")

            # Парсим каждый товар
            for i, product_url in enumerate(all_product_links, 1):
                print(f"Парсим товар {i}/{len(all_product_links)}: {product_url}")

                product = await self.parse_product_card(page, product_url)
                if product:
                    self.products.append(product)
                    print(f"  ✓ {product.title}")
                else:
                    print("  ✗ Не удалось спарсить")

                # Небольшая пауза между запросами
                await asyncio.sleep(1)

        finally:
            await browser.close()
            if self.playwright:
                await self.playwright.stop()

    def save_results(self, filename: str = "mosigra_products.json"):
        """Сохранение результатов в JSON файл"""
        try:
            data = [product.model_dump() for product in self.products]

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"Сохранено {len(self.products)} товаров в файл {filename}"
            )

            # Сохраняем также список неудачных URL
            if self.failed_urls:
                failed_filename = "failed_urls.txt"
                with open(failed_filename, "w", encoding="utf-8") as f:
                    for url in self.failed_urls:
                        f.write(f"{url}\n")
                self.logger.warning(
                    f"Список неудачных URL сохранен в {failed_filename}"
                )

        except Exception as e:
            self.logger.error(f"Ошибка при сохранении результатов: {e}")

    def get_statistics(self) -> dict:
        """Получение статистики парсинга"""
        total_products = len(self.products)
        failed_count = len(self.failed_urls)
        success_rate = (
            (total_products / (total_products + failed_count) * 100)
            if (total_products + failed_count) > 0
            else 0
        )

        stats = {
            "total_products": total_products,
            "failed_urls": failed_count,
            "success_rate": round(success_rate, 2),
            "products_with_price": len([
                p for p in self.products if p.price_rub is not None
            ]),
            "products_with_manufacturer": len([
                p for p in self.products if p.manufacturer is not None
            ]),
            "products_with_year": len([p for p in self.products if p.year is not None]),
            "products_with_description": len([
                p for p in self.products if p.description is not None
            ]),
        }

        return stats


async def main():
    # Создаем парсер с настройками retry
    parser = MosigraParser(max_retries=3, retry_delay=2)

    try:
        # Запускаем парсер с ограничениями для тестирования
        await parser.run(max_pages=2, max_products=10)

        # Сохраняем результаты
        parser.save_results()

        # Получаем и выводим подробную статистику
        stats = parser.get_statistics()

        print(f"\n{'=' * 50}")
        print("СТАТИСТИКА ПАРСИНГА")
        print(f"{'=' * 50}")
        print(f"Всего товаров спаршено: {stats['total_products']}")
        print(f"Неудачных попыток: {stats['failed_urls']}")
        print(f"Процент успеха: {stats['success_rate']}%")
        print(f"Товаров с ценой: {stats['products_with_price']}")
        print(f"Товаров с производителем: {stats['products_with_manufacturer']}")
        print(f"Товаров с годом выпуска: {stats['products_with_year']}")
        print(f"Товаров с описанием: {stats['products_with_description']}")

        if parser.products:
            print("\nПример спаршенного товара:")
            example = parser.products[0]
            print(f"  Название: {example.title}")
            print(f"  URL: {example.url}")
            print(
                f"  Цена: {example.price_rub} руб."
                if example.price_rub
                else "  Цена: не указана"
            )
            print(
                f"  Производитель: {example.manufacturer}"
                if example.manufacturer
                else "  Производитель: не указан"
            )
            print(f"  Год: {example.year}" if example.year else "  Год: не указан")
            print(
                f"  Игроки: {example.players}"
                if example.players
                else "  Игроки: не указано"
            )
            print(
                f"  Время игры: {example.play_time}"
                if example.play_time
                else "  Время игры: не указано"
            )
            print(
                f"  Возраст: {example.age}" if example.age else "  Возраст: не указан"
            )
            if example.description:
                print(
                    f"  Описание: {example.description[:100]}..."
                    if len(example.description) > 100
                    else f"  Описание: {example.description}"
                )

        print("\nРезультаты сохранены в файл mosigra_products.json")
        if parser.failed_urls:
            print("Неудачные URL сохранены в файл failed_urls.txt")

    except KeyboardInterrupt:
        print("\nПарсинг прерван пользователем")
        parser.save_results()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        parser.save_results()


if __name__ == "__main__":
    asyncio.run(main())
