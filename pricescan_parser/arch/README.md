# PriceScan Parser

Парсер для сбора данных о ценах настольных игр с различных интернет-магазинов.

## Поддерживаемые сайты

### HobbyGames.ru (BeautifulSoup парсер)

Парсер для [HobbyGames.ru](https://hobbygames.ru/) - крупнейшего магазина настольных игр в России.

**Возможности:**
- Поиск товаров по названию
- Парсинг полной информации о товаре
- Извлечение цен, наличия, характеристик игр
- Поддержка изображений товаров
- Извлечение рейтингов и отзывов

## Установка

```bash
cd pricescan_parser
pip install -e .
```

## Использование

### Базовое использование

```python
import asyncio
from hobbydames import HobbyGamesParser

async def main():
    parser = HobbyGamesParser()
    
    # Поиск товаров
    results = await parser.search_products("Колонизаторы", limit=5)
    
    for product in results.products:
        print(f"{product.title} - {product.price} {product.currency}")
    
    # Парсинг конкретного товара
    product = await parser.parse_product_url("https://hobbygames.ru/catan-kolonizatory")
    
    if product:
        print(f"Название: {product.title}")
        print(f"Цена: {product.price} {product.currency}")
        print(f"Игроки: {product.players_min}-{product.players_max}")
        print(f"Время: {product.playtime_min} мин")
        print(f"Возраст: {product.age_min}+")
    
    await parser.close()

asyncio.run(main())
```

### Обратная совместимость

```python
from hobbydames import BSParser

async def main():
    parser = BSParser()
    
    # Старый интерфейс
    result = await parser.parse_product("https://hobbygames.ru/some-game")
    
    print(result)  # dict с базовой информацией
    
    await parser.close()

asyncio.run(main())
```

## Тестирование

Запуск тестов парсера:

```bash
python test_hobbygames.py
```

Демонстрация работы:

```bash
python main.py
```

## Структура проекта

```
pricescan_parser/
├── hobbydames/              # Парсер для HobbyGames.ru
│   ├── __init__.py         # Экспорт публичных классов
│   ├── client.py           # HTTP клиент
│   ├── models.py           # Pydantic модели данных
│   └── parser.py           # Основная логика парсинга
├── main.py                 # Демо-скрипт
├── test_hobbygames.py      # Тесты парсера
├── pyproject.toml          # Зависимости проекта
└── README.md              # Документация
```

## Модели данных

### ProductInfo
Основная модель товара с полной информацией:
- `title` - название товара
- `price` - цена (Decimal)
- `currency` - валюта (по умолчанию "RUB")
- `availability` - статус наличия
- `is_available` - флаг наличия (bool)
- `url` - ссылка на товар
- `image_url` - ссылка на изображение
- `players_min/max` - количество игроков
- `playtime_min` - время игры в минутах
- `age_min` - минимальный возраст
- `description` - описание товара
- `rating` - рейтинг товара
- `reviews_count` - количество отзывов

### SearchResult
Результат поиска товаров:
- `query` - поисковый запрос
- `total_found` - количество найденных товаров
- `page` - текущая страница
- `products` - список товаров (List[ProductInfo])

## Интеграция с Django API

Парсер интегрируется с Django API через Celery задачи в `pricescan_api/product/tasks.py`:

```python
from pricescan_parser.hobbydames import HobbyGamesParser

@shared_task(queue="light")
async def parse_hobbygames_product(product_id: int, url: str):
    parser = HobbyGamesParser()
    
    try:
        product_info = await parser.parse_product_url(url)
        
        if product_info:
            # Обновляем данные в БД
            # ...
            
    finally:
        await parser.close()
```

## Планы развития

- [ ] Парсер для других магазинов (Ozon, Wildberries)
- [ ] Playwright парсер для SPA сайтов
- [ ] API JSON парсер для открытых API
- [ ] Кэширование результатов
- [ ] Обработка капчи и антибот защиты
- [ ] Прокси поддержка
