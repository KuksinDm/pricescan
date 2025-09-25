# 🛒 PriceScan - Система мониторинга цен

Многосервисное приложение для отслеживания цен на товары с интеграцией Telegram-бота.

## 🏗️ Архитектура

### Основные компоненты:
- **Django API** - основной бэкенд с PostgreSQL, Celery, Redis
- **Telegram Bot** - интерфейс для пользователей (aiogram 3.x)
- **3 типа парсеров:**
  - BeautifulSoup парсер (HobbyGames, Wildberries)
  - Playwright парсер (Mosigra, SPA сайты)
  - API JSON парсер (Wildberries API)
- **Nginx** - реверс-прокси и статика

### Технологический стек:
- **Backend:** Django 5.x, DRF, PostgreSQL, Celery, Redis
- **Bot:** aiogram 3.x, aiohttp
- **Parsers:** BeautifulSoup4, Playwright, httpx
- **Infrastructure:** Docker, Docker Compose, Nginx
- **Documentation:** drf-spectacular (Swagger/OpenAPI)

## 🚀 Быстрый старт

### Предварительные требования:
- Docker & Docker Compose
- Git

### Запуск проекта:

1. **Клонирование репозитория:**
```bash
git clone <repository-url>
cd pricescan
```

2. **Настройка переменных окружения:**
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

3. **Запуск всех сервисов:**
```bash
docker-compose up -d
```

4. **Инициализация базы данных:**
```bash
docker-compose exec web_pricescan python manage.py migrate
docker-compose exec web_pricescan python manage.py loaddata initial_data.json
```

5. **Создание суперпользователя:**
```bash
docker-compose exec web_pricescan python manage.py createsuperuser
```

### Доступ к сервисам:

- **API Documentation:** http://localhost:9040/api/docs/
- **Admin Panel:** http://localhost:9040/admin/
- **API Base URL:** http://localhost:9040/api/

## 📱 Функциональность

### Для пользователей:
- �� **Поиск товаров** - найдите самую низкую цену
- 💰 **Отслеживание цен** - настройте алерты на снижение цен
- ⭐ **Избранное** - сохраните понравившиеся товары
- �� **История цен** - просматривайте динамику изменения цен
- 🔄 **Обновление данных** - запросите актуальные цены

### Для администраторов:
- �� **Управление магазинами** - добавление новых источников
- 🤖 **Мониторинг парсеров** - отслеживание работы парсеров
- 📈 **Аналитика** - статистика по товарам и пользователям
- ⚙️ **Настройка расписания** - автоматическое обновление цен

## �� Поддерживаемые магазины

| Магазин | Тип парсера | Статус |
|---------|-------------|--------|
| HobbyGames | BeautifulSoup | ✅ |
| Wildberries | API JSON | ✅ |
| Mosigra | Playwright | ✅ |

## �� API Endpoints

### Основные эндпоинты:

- `GET /api/products/` - список товаров
- `GET /api/products/cheapest/` - самое дешевое предложение
- `POST /api/products/{id}/refresh/` - обновить цены товара
- `GET /api/products/{id}/price-history/` - история цен
- `GET /api/stats/` - статистика системы

### Аутентификация:
- `POST /api/auth/jwt/create/` - получение JWT токена
- `POST /api/auth/jwt/refresh/` - обновление токена

Полная документация доступна в Swagger UI: http://localhost:9040/api/docs/

## 🤖 Telegram Bot

Бот предоставляет удобный интерфейс для всех функций системы:

- `/start` - регистрация и приветствие
- 🔍 **Поиск** - найдите товар по названию
- ⭐ **Избранное** - управление списком избранных товаров
- 🚨 **Алерты** - настройка уведомлений о снижении цен
- 📊 **История** - просмотр истории поисков

## 🐳 Docker Services

```yaml
services:
  db_pricescan        # PostgreSQL 15
  web_pricescan       # Django API
  bot_pricescan       # Telegram Bot
  redis              # Redis для Celery
  celery_worker      # Celery Worker
  celery_beat        # Celery Beat Scheduler
  pricescan_parser   # BeautifulSoup + API парсеры
  pricescan_playwright # Playwright парсер
  nginx_pricescan    # Nginx реверс-прокси
```

## 📊 Мониторинг и логирование

- **Логи парсеров:** `logs/parser_results.log`
- **Логи пользователей:** `logs/user.log`
- **Логи товаров:** `logs/product.log`
- **Логи неудачных запросов:** `logs/failed_requests.log`

## �� Автоматические задачи

- **Обновление цен:** каждые 6 часов
- **Массовый парсинг:** каждые 3 дня
- **Мониторинг избранного:** каждые 2 часа
- **Проверка алертов:** при каждом обновлении цен

## 🛠️ Разработка

### Локальная разработка:

```bash
# Запуск только базы данных и Redis
docker-compose up -d db_pricescan redis

# Установка зависимостей
pip install -r requirements.txt

# Запуск Django в режиме разработки
python manage.py runserver

# Запуск Celery worker
celery -A config worker --loglevel=info

# Запуск Telegram бота
python -m pricescan_bot.main
```

### Тестирование:

```bash
# Тесты API
python manage.py test

# Тесты парсеров
pytest pricescan_parser/tests/
pytest pricescan_playwright/tests/

# Тесты бота
pytest pricescan_bot/tests/
```

## 📝 Лицензия

MIT License

## 👥 Автор

[Ваше имя] - [email@example.com]

---

**PriceScan** - умный помощник для экономии на покупках! ��💰