# PriceScan Bot

Требуется Python 3.12+.

1) Установить зависимости:
```
uv sync
```

2) Создать .env:
```
BOT_TOKEN=123:ABC
API_BASE_URL=http://localhost:8000/api/
BOT_SERVICE_TOKEN=change-me
```

3) Запуск:
```
uv run python -m pricescan_bot.main
```


