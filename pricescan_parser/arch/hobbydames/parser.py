import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .client import HobbyGamesClient
from .models import ProductInfo, SearchResult

logger = logging.getLogger(__name__)


class HobbyGamesParser:
    """Парсер для HobbyGames.ru"""

    def __init__(self):
        self.client = HobbyGamesClient()

    async def search_products(self, query: str, limit: int = 20) -> SearchResult:
        """Поиск товаров по названию"""
        try:
            search_url = f"https://hobbygames.ru/search/?q={query}"
            soup = await self.client.get_page(search_url)

            if not soup:
                return SearchResult(query=query, total_found=0, products=[])

            products = []
            # Ищем товары в результатах поиска
            product_cards = soup.find_all(
                ["div", "article"], class_=re.compile(r"product|item|card")
            )

            for card in product_cards[:limit]:
                product = await self._parse_product_card(card)
                if product:
                    products.append(product)

            return SearchResult(
                query=query, total_found=len(products), products=products
            )

        except Exception as e:
            logger.error(f"Ошибка поиска товаров: {e}")
            return SearchResult(query=query, total_found=0, products=[])

    async def parse_product_url(self, url: str) -> Optional[ProductInfo]:
        """Парсинг конкретного товара по URL"""
        try:
            soup = await self.client.get_product_page(url)
            if not soup:
                return None

            return await self._parse_product_page(soup, url)

        except Exception as e:
            logger.error(f"Ошибка парсинга товара {url}: {e}")
            return None

    async def _parse_product_card(self, card: Tag) -> Optional[ProductInfo]:
        """Парсинг карточки товара из списка"""
        try:
            # Название товара
            title_elem = card.find(
                ["h1", "h2", "h3", "h4"], class_=re.compile(r"title|name")
            )
            if not title_elem:
                title_elem = card.find("a", title=True)

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            if title_elem.name == "a":
                title = title_elem.get("title", title)

            # URL товара
            link_elem = card.find("a", href=True)
            if not link_elem:
                return None

            url = urljoin(self.client.BASE_URL, link_elem["href"])

            # Цена
            price = self._extract_price_from_element(card)

            # Изображение
            img_elem = card.find("img")
            image_url = None
            if img_elem and img_elem.get("src"):
                image_url = urljoin(self.client.BASE_URL, img_elem["src"])

            return ProductInfo(
                title=title,
                price=price,
                url=url,
                image_url=image_url,
                availability="В наличии" if price else "Нет в наличии",
                is_available=bool(price),
            )

        except Exception as e:
            logger.error(f"Ошибка парсинга карточки товара: {e}")
            return None

    async def _parse_product_page(
        self, soup: BeautifulSoup, url: str
    ) -> Optional[ProductInfo]:
        """Парсинг полной страницы товара"""
        try:
            # Название
            title = self._extract_title(soup)
            if not title:
                return None

            # Цена
            price = self._extract_price_from_element(soup)

            # Наличие
            availability = self._extract_availability(soup)
            is_available = "в наличии" in availability.lower() or bool(price)

            # Изображение
            image_url = self._extract_image_url(soup)

            # Характеристики игры
            players_min, players_max = self._extract_players_count(soup)
            playtime_min = self._extract_playtime(soup)
            age_min = self._extract_age(soup)

            # Описание
            description = self._extract_description(soup)

            # Рейтинг и отзывы
            rating, reviews_count = self._extract_rating(soup)

            # Автор и издатель
            author = self._extract_author(soup)
            publisher = self._extract_publisher(soup)

            return ProductInfo(
                title=title,
                price=price,
                url=url,
                image_url=image_url,
                availability=availability,
                is_available=is_available,
                players_min=players_min,
                players_max=players_max,
                playtime_min=playtime_min,
                age_min=age_min,
                description=description,
                rating=rating,
                reviews_count=reviews_count,
                author=author,          # Добавить
                publisher=publisher,    # Добавить
            )

        except Exception as e:
            logger.error(f"Ошибка парсинга страницы товара: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение названия товара"""
        selectors = [
            "h1.product-title",
            'h1[class*="title"]',
            'h1[class*="name"]',
            ".product-name h1",
            ".product-title",
            "h1",
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        return None

    def _extract_price_from_element(self, element) -> Optional[Decimal]:
        """Извлечение цены из элемента"""
        price_selectors = ['[class*="price"]', "[data-price]", ".cost", ".value"]

        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self._parse_price(price_text)
                if price:
                    return price
        return None

    def _parse_price(self, price_text: str) -> Optional[Decimal]:
        """Парсинг цены из текста"""
        if not price_text:
            return None

        # Убираем все кроме цифр, точек и запятых
        price_clean = re.sub(r"[^\d\.,]", "", price_text)

        if not price_clean:
            return None

        # Заменяем запятую на точку
        price_clean = price_clean.replace(",", ".")

        try:
            return Decimal(price_clean)
        except InvalidOperation:
            return None

    def _extract_availability(self, soup: BeautifulSoup) -> str:
        """Извлечение информации о наличии"""
        availability_selectors = [
            ".availability",
            ".stock",
            '[class*="available"]',
            '[class*="stock"]',
        ]

        for selector in availability_selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)

        return "Неизвестно"

    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение URL главного изображения"""
        img_selectors = [
            ".product-image img",
            ".main-image img",
            ".gallery img",
            'img[class*="product"]',
        ]

        for selector in img_selectors:
            img = soup.select_one(selector)
            if img and img.get("src"):
                return urljoin(self.client.BASE_URL, img["src"])
        return None

    def _extract_players_count(
        self, soup: BeautifulSoup
    ) -> tuple[Optional[int], Optional[int]]:
        """Извлечение количества игроков"""
        # Ищем характеристики игры
        specs = soup.find_all(text=re.compile(r"игрок|player", re.I))

        for spec in specs:
            parent = spec.parent
            if parent:
                text = parent.get_text()
                # Ищем паттерны типа "2-4 игрока", "1-6 players"
                match = re.search(r"(\d+)[-–—]\s*(\d+)", text)
                if match:
                    return int(match.group(1)), int(match.group(2))

                # Ищем одиночные числа
                match = re.search(r"(\d+)", text)
                if match:
                    num = int(match.group(1))
                    return num, num

        return None, None

    def _extract_playtime(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлечение времени игры в минутах"""
        time_specs = soup.find_all(text=re.compile(r"минут|время|time", re.I))

        for spec in time_specs:
            parent = spec.parent
            if parent:
                text = parent.get_text()
                # Ищем числа перед "минут"
                match = re.search(r"(\d+)\s*(?:минут|мин|min)", text, re.I)
                if match:
                    return int(match.group(1))

        return None

    def _extract_age(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлечение возрастного ограничения"""
        age_specs = soup.find_all(text=re.compile(r"лет|возраст|age|\+", re.I))

        for spec in age_specs:
            parent = spec.parent
            if parent:
                text = parent.get_text()
                # Ищем паттерны типа "10+", "от 12 лет"
                match = re.search(r"(?:от\s*)?(\d+)\s*(?:\+|лет|age)", text, re.I)
                if match:
                    return int(match.group(1))

        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение описания товара"""
        desc_selectors = [
            ".description",
            ".product-description",
            '[class*="desc"]',
            ".content",
        ]

        for selector in desc_selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)[:500]  # Ограничиваем длину

        return None

    def _extract_rating(
        self, soup: BeautifulSoup
    ) -> tuple[Optional[float], Optional[int]]:
        """Извлечение рейтинга и количества отзывов"""
        rating = None
        reviews_count = None

        # Поиск рейтинга
        rating_elem = soup.select_one('[class*="rating"], [class*="star"]')
        if rating_elem:
            rating_text = rating_elem.get_text()
            match = re.search(r"(\d+(?:\.\d+)?)", rating_text)
            if match:
                try:
                    rating = float(match.group(1))
                except ValueError:
                    pass

        # Поиск количества отзывов
        reviews_elem = soup.select_one('[class*="review"], [class*="comment"]')
        if reviews_elem:
            reviews_text = reviews_elem.get_text()
            match = re.search(r"(\d+)", reviews_text)
            if match:
                try:
                    reviews_count = int(match.group(1))
                except ValueError:
                    pass

        return rating, reviews_count

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение автора игры"""
        author_selectors = [
            '[class*="author"]',
            '[class*="designer"]',
            ".game-info .author",
            ".product-specs .author",
        ]

        for selector in author_selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)

        # Ищем в тексте паттерны "Автор: ..." или "Дизайнер: ..."
        text_patterns = soup.find_all(text=re.compile(r"автор|дизайнер|designer", re.I))
        for pattern in text_patterns:
            parent = pattern.parent
            if parent:
                text = parent.get_text()
                match = re.search(
                    r"(?:автор|дизайнер|designer):\s*([^,\n]+)", text, re.I
                )
                if match:
                    return match.group(1).strip()

        return None

    def _extract_publisher(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение издателя"""
        publisher_selectors = [
            '[class*="publisher"]',
            '[class*="brand"]',
            ".game-info .publisher",
            ".product-specs .publisher",
        ]

        for selector in publisher_selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)

        # Ищем паттерны "Издатель: ..." или "Производитель: ..."
        text_patterns = soup.find_all(
            text=re.compile(r"издатель|производитель|publisher", re.I)
        )
        for pattern in text_patterns:
            parent = pattern.parent
            if parent:
                text = parent.get_text()
                match = re.search(
                    r"(?:издатель|производитель|publisher):\s*([^,\n]+)", text, re.I
                )
                if match:
                    return match.group(1).strip()

        return None

    async def close(self):
        """Закрыть клиент"""
        await self.client.close()


# Для обратной совместимости
class BSParser(HobbyGamesParser):
    """Алиас для обратной совместимости"""

    async def parse_product(self, url: str) -> Optional[dict]:
        """Старый интерфейс для совместимости"""
        product = await self.parse_product_url(url)
        if not product:
            return None

        return {
            "title": product.title,
            "price": float(product.price) if product.price else None,
            "availability": product.availability,
            "url": str(product.url),
            "is_available": product.is_available,
        }
