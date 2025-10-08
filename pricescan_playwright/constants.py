# pricescan_playwright/constants.py
DEFAULT_TIMEOUT = 12
DEFAULT_LIMIT = 1000
DEFAULT_CONCURRENCY = 6
DEFAULT_TIMEOUT_MS = 30000
DEFAULT_SELECTOR_TIMEOUT = 2500
DEFAULT_COOKIE_TIMEOUT = 500
DEFAULT_AGE_GATE_TIMEOUT = 800
DEFAULT_AUTO_SCROLL_TIMEOUT = 10000
DEFAULT_SCROLL_DELAY = 350
DEFAULT_UI_DELAY = 200
DEFAULT_PAGE_WAIT = 300
DEFAULT_RESULTS_PER_PAGE = 48
DEFAULT_MAX_PAGES = 12
DEFAULT_PAGE_START = 1

# Селекторы для извлечения данных
TITLE_SELECTORS = [
    'meta[property="og:title"]',
    'meta[name="og:title"]',
    "h1",
    ".card_title",
    ".ProductCard__title",
    '[itemprop="name"]',
]

PRICE_SELECTORS = [
    'meta[itemprop="price"]',
    '[itemprop="price"]',
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
]

CATEGORY_SELECTORS = [
    "article.categories a.categories_link",
    ".categories a.categories_link",
    "a.categories_link",
    ".categories a",
    ".breadcrumbs a",
    ".breadcrumb a",
]

PRODUCT_LINK_SELECTORS = [
    "#productsContainer article.card a.card__title",
    "#productsContainer article.card a.card__image",
    ".products-container article.card a.card__title",
    ".products-container article.card a.card__image",
]

COOKIE_SELECTORS = [
    'button:has-text("Согласен")',
    'button:has-text("Принять")',
    'button:has-text("Ок")',
    'button:has-text("Хорошо")',
    'button:has-text("Понятно")',
    '[data-testid="cookie-accept"]',
    'button[aria-label="Закрыть"]',
]

AGE_GATE_SELECTORS = [
    'button:has-text("Подтвердить")',
    'button:has-text("Да, мне есть 18")',
    'button:has-text("Мне есть 18")',
    'button:has-text("Продолжить")',
    '.modal-dialog button:has-text("Подтвердить")',
    '.modal button:has-text("18")',
]

# Селекторы для контейнеров и контента
CONTAINER_SELECTORS = [
    "#productsContainer",
    ".products-container",
    ".products-content",
    "section.category-content",
]

CONTAINER_SELECTOR = ":is(#productsContainer, .products-container, .products-content, section.category-content)"

PRODUCT_CARD_SELECTORS = ["article.card", ".card", ".product-card", "[data-product-id]"]

PRODUCT_CARD_SELECTOR = "article.card, .card, .product-card, [data-product-id]"

CONTENT_SELECTORS = ["main", "h1", ".card_title", ".ProductCard__title"]

CONTENT_SELECTOR = "main, h1, .card_title, .ProductCard__title"

EXCLUDED_CATEGORIES = {
    "Главная",
    "Каталог",
    "Настольные игры",
    "Аксессуары",
    "Прочее",
    "Мосигра",
    "Mosigra",
}

BLACKLIST_SUBSTR = (
    "/contacts",
    "/games-lib",
    "/magaziny",
    "/shops",
    "/store",
    "/stores",
    "/delivery",
    "/oplata",
    "/payment",
    "/blog",
    "/news",
    "/about",
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
