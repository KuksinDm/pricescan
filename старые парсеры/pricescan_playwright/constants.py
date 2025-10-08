DEFAULT_TIMEOUT = 12
DEFAULT_LIMIT = 1000
DEFAULT_CONCURRENCY = 6

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
