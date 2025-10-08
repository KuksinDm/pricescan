"""Константы для BeautifulSoup парсера"""

# HTTP настройки
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_DELAY = 0.5
DEFAULT_MAX_RETRIES = 3

# Парсинг настройки
DEFAULT_LIMIT = 1000
DEFAULT_REQUEST_DELAY = 0.5

# Селекторы для HobbyGames (из рабочей версии)
HOBBYGAMES_SELECTORS = {
    "title": [".product-info__main h1", "h1"],
    "price": [
        ".product-card-price__current",
        ".product-card-price_current",
        ".product-price__current",
        ".product-price, .price",
    ],
    "manufacturers": [
        "a.manufacturers__value",  # Основной селектор из рабочей версии
        ".manufacturers a",
        "a[href*='manufacturer']",
    ],
    "categories": [
        ".breadcrumbs__link",  # Из рабочей версии
        ".tags a",  # Из рабочей версии
    ],
    "product_links": [
        ".product-card-title a",  # Из рабочей версии
        ".product-card__title a",
        "a.catalog-item__title",
        "a.product-item-title",
    ],
    "product_cards": [
        '[data-entity="parent-container"]',
        ".product-item",
        ".catalog__items .catalog__item",
        ".items .item",
    ],
    "game_tags": [
        ".product-tag",  # Из рабочей версии
    ],
}

# Фильтры для категорий
EXCLUDED_CATEGORIES = [
    "Главная",
    "Каталог",
    "Настольные игры",
    "Аксессуары",
    "Прочее",
    "Hobby Games",
    "Hobby World",
]


# User-Agent
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)

# Логирование
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 10
