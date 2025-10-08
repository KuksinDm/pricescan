import re
from typing import List, Optional, Tuple

from django.utils.text import slugify
from unidecode import unidecode

from ..constants import DEFAULT_CATEGORY, DEFAULT_PUBLISHER, MINUTES_PER_HOUR
from ..models import Category, Publisher


class GameDataParser:
    """Парсер игровых данных"""

    @staticmethod
    def parse_publishers(publisher_str: str) -> List[Publisher]:
        """Парсинг издателей"""
        if not publisher_str:
            publisher_str = DEFAULT_PUBLISHER

        publisher_names = GameDataParser.split_by_comma(publisher_str)
        publishers = []

        for name in publisher_names:
            if name:
                publisher, _ = Publisher.objects.get_or_create(
                    name=name, defaults={"slug": slugify(unidecode(name))}
                )
                publishers.append(publisher)

        return (
            publishers
            if publishers
            else [GameDataParser._get_or_create_publisher(DEFAULT_PUBLISHER)]
        )

    @staticmethod
    def _get_or_create_publisher(name: str) -> Publisher:
        """Получение или создание издателя"""
        safe_name = name or DEFAULT_PUBLISHER
        publisher, created = Publisher.objects.get_or_create(
            name=safe_name, defaults={"slug": slugify(unidecode(safe_name))}
        )
        return publisher

    @staticmethod
    def parse_categories(category_str: str) -> List[Category]:
        """Парсинг категорий"""
        if not category_str:
            category_str = DEFAULT_CATEGORY

        category_names = GameDataParser.split_by_comma(category_str)
        categories = []

        for name in category_names:
            if name:
                category, _ = Category.objects.get_or_create(
                    name=name, defaults={"slug": slugify(unidecode(name))}
                )
                categories.append(category)

        return (
            categories
            if categories
            else [GameDataParser._get_or_create_category(DEFAULT_CATEGORY)]
        )

    @staticmethod
    def _get_or_create_category(name: str) -> Category:
        """Получение или создание категории"""
        safe_name = name or DEFAULT_CATEGORY
        category, created = Category.objects.get_or_create(
            name=name, defaults={"slug": slugify(unidecode(safe_name))}
        )
        return category

    @staticmethod
    def split_by_comma(text: str) -> List[str]:
        """Разделение строки по запятым"""
        return [name.strip() for name in text.split(",")]

    @staticmethod
    def parse_players_range(players_str: str) -> Optional[Tuple[int, int]]:
        """Парсинг диапазона игроков из строки

        Поддерживает форматы:
        - "от 2 до 4" -> (2, 4)
        - "2-4" -> (2, 4)
        - "4+" -> (4, 4)
        - "4" -> (4, 4)
        """
        if not players_str:
            return None

        normalized_str = (
            str(players_str).strip().lower().replace("–", "-").replace("—", "-")
        )

        # Диапазон "от X до Y" или "X-Y"
        range_match = re.search(
            r"от\s*(\d+)\s*до\s*(\d+)", normalized_str
        ) or re.search(r"(\d+)\s*-\s*(\d+)", normalized_str)
        if range_match:
            min_players, max_players = (
                int(range_match.group(1)),
                int(range_match.group(2)),
            )
            return (min(min_players, max_players), max(min_players, max_players))

        # Одиночное число с "+" или без
        single_match = re.search(r"(\d+)\s*\+", normalized_str) or re.search(
            r"\b(\d+)\b", normalized_str
        )
        if single_match:
            players_count = int(single_match.group(1))
            return (players_count, players_count)

        return None

    @staticmethod
    def parse_age(age_str: str) -> Optional[int]:
        """Парсинг возраста"""
        if not age_str:
            return None

        try:
            age_clean = age_str.replace("+", "").strip()
            return int(age_clean)
        except ValueError:
            return None

    @staticmethod
    def parse_playtime(playtime_str: str) -> Optional[int]:
        """Парсинг времени игры → минимальные минуты

        Поддерживает форматы:
        - "1 ч 30 мин" -> 90
        - "1-2 часа" -> 60
        - "30-60 мин" -> 30
        - "60+" -> 60 или 3600 (зависит от контекста)
        """
        if not playtime_str:
            return None

        normalized_str = playtime_str.lower().replace("\xa0", " ").strip()

        # "1 ч 30 мин" -> 90 минут
        hours_minutes_match = re.search(
            r"(\d+)\s*ч(?:ас(?:а|ов)?)?\s*(\d+)\s*мин", normalized_str
        )
        if hours_minutes_match:
            hours = int(hours_minutes_match.group(1))
            minutes = int(hours_minutes_match.group(2))
            return hours * MINUTES_PER_HOUR + minutes

        # "1-2 часа" / "1 ч" -> 60 минут
        hours_match = re.search(
            r"(\d+)\s*(?:[–-]\s*\d+\s*)?(?:ч|час(?:а|ов)?)", normalized_str
        )
        if hours_match:
            hours = int(hours_match.group(1))
            return hours * MINUTES_PER_HOUR

        # "30-60 мин" / "30 мин" -> 30 минут
        minutes_match = re.search(
            r"(?:от\s*)?(\d+)\s*(?:до\s*\d+\s*)?мин", normalized_str
        ) or re.search(r"(?:от\s*)?(\d+)\s*(?:[–-]\s*\d+)?\s*мин", normalized_str)
        if minutes_match:
            return int(minutes_match.group(1))

        # "30-60" (без единиц) -> 30 минут
        range_match = re.search(r"(\d+)\s*[–-]\s*\d+", normalized_str)
        if range_match:
            return int(range_match.group(1))

        # "60+" -> проверяем контекст (часы или минуты)
        plus_match = re.search(r"(\d+)\s*\+", normalized_str)
        if plus_match:
            number = int(plus_match.group(1))
            is_hours = re.search(r"(?:^|\s)(?:ч|час)", normalized_str)
            return number * MINUTES_PER_HOUR if is_hours else number

        # Фолбэк: первое число с проверкой контекста
        fallback_match = re.search(r"(\d+)", normalized_str)
        if fallback_match:
            number = int(fallback_match.group(1))
            is_hours = re.search(r"(?:^|\s)(?:ч|час)", normalized_str)
            return number * MINUTES_PER_HOUR if is_hours else number

        return None
