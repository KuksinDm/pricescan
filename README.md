# PriceScan - Система мониторинга цен

Мощная система для отслеживания цен на товары с поддержкой алертов, мониторинга и Telegram бота.

## 🚀 Возможности

- **3 типа парсеров**: BeautifulSoup, Playwright, API JSON
- **Django REST API** с PostgreSQL, Redis, Celery
- **JWT аутентификация** через Telegram
- **Система алертов** на изменение цен с уведомлениями
- **Мониторинг производительности** и состояния системы
- **Telegram бот** для удобного взаимодействия
- **Swagger документация** API
- **Docker контейнеризация** всех сервисов
- **Prometheus + Grafana** для мониторинга
- **Автоматическое тестирование** и CI/CD
- **Безопасность** с rate limiting и CORS

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   Django API    │    │   Nginx Proxy   │
│   (aiogram)     │◄──►│   (Django)      │◄──►│   (Reverse)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │   + Redis       │
                       └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  BS4 Parser     │ │ Playwright      │ │  API JSON       │
    │  (HobbyGames)   │ │ (Mosigra)       │ │ (Wildberries)   │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 🛠️ Технологический стек

### Backend
- **Django 4.2** - веб-фреймворк
- **PostgreSQL** - основная база данных
- **Redis** - кэш и брокер сообщений
- **Celery** - асинхронные задачи
- **Django REST Framework** - API
- **JWT** - аутентификация

### Парсеры
- **BeautifulSoup** - парсинг HTML
- **Playwright** - парсинг SPA
- **httpx** - HTTP клиент для API

### Frontend
- **Telegram Bot** (aiogram)
- **Swagger UI** - документация API

### DevOps
- **Docker & Docker Compose**
- **Nginx** - reverse proxy
- **Prometheus** - мониторинг (планируется)

## 📦 Установка и запуск

### Требования
- Docker & Docker Compose
- Python 3.11+ (для локальной разработки)

### Быстрый старт

1. **Клонируйте репозиторий**
```bash
git clone <repository-url>
cd pricescan
```

2. **Создайте .env файл**
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

3. **Запустите все сервисы**
```bash
docker-compose up -d
```

4. **Выполните миграции**
```bash
docker-compose exec web_pricescan python manage.py migrate
```

5. **Создайте суперпользователя**
```bash
docker-compose exec web_pricescan python manage.py createsuperuser
```

6. **Загрузите тестовые данные**
```bash
docker-compose exec web_pricescan python manage.py loaddata fixtures/initial_data.json
```

### Доступ к сервисам

- **API**: http://localhost:9040/api/
- **Swagger UI**: http://localhost:9040/api/docs/
- **Admin**: http://localhost:9040/admin/
- **Parser BS4**: http://localhost:8001/
- **Parser Playwright**: http://localhost:8002/

## 🔧 Конфигурация

### Переменные окружения (.env)

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DB=pricescan_db
POSTGRES_USER=pricescan_user
POSTGRES_PASSWORD=pricescan_password
POSTGRES_HOST=db_pricescan

# Redis
REDIS_URL=redis://redis:6379/0

# Telegram Bot
BOT_TOKEN=your-telegram-bot-token
BOT_SERVICE_TOKEN=your-service-token

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

## 📚 API Документация

### Основные endpoints

#### Продукты
- `GET /api/products/` - список продуктов
- `GET /api/products/cheapest/?q=настольная игра` - самый дешевый товар
- `POST /api/products/{id}/refresh/` - обновить цены

#### Алерты
- `GET /api/alerts/` - список алертов пользователя
- `POST /api/alerts/` - создать алерт
- `POST /api/alerts/{id}/toggle/` - переключить статус
- `GET /api/alerts/{id}/history/` - история срабатываний

#### Мониторинг
- `GET /api/monitoring/overview/` - обзор системы
- `GET /api/monitoring/metrics/` - метрики
- `GET /api/monitoring/health/` - состояние сервисов

### Аутентификация

```bash
# Получение JWT токена
curl -X POST http://localhost:9040/api/auth/jwt/create/ \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789, "telegram_username": "username"}'

# Использование токена
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:9040/api/products/
```

## 🤖 Telegram Bot

### Команды бота

- `/start` - начать работу
- `/help` - справка
- `Поиск` - найти самый дешевый товар
- `История` - история поиска
- `Избранное` - избранные товары
- `Алерты` - управление алертами

### Пример использования

1. Отправьте боту `/start`
2. Нажмите "Поиск"
3. Введите название товара (например, "настольная игра")
4. Получите самый дешевый вариант
5. Добавьте в избранное или создайте алерт

## 📊 Мониторинг

### Метрики системы

- **Производительность API**: время ответа, количество запросов
- **Состояние сервисов**: доступность парсеров, БД, Redis
- **Алерты**: количество активных алертов, срабатывания
- **Парсинг**: статистика парсинга по магазинам

### Логирование

Логи сохраняются в папке `logs/`:
- `project.log` - общие логи Django
- `product.log` - логи продуктов
- `user.log` - логи пользователей
- `parser_results.log` - результаты парсинга
- `failed_requests.log` - неудачные запросы

## 🔄 Парсинг

### Типы парсеров

1. **BeautifulSoup** - для простых HTML сайтов
   - HobbyGames.ru
   - Быстрый парсинг статического контента

2. **Playwright** - для SPA и JavaScript сайтов
   - Mosigra.ru
   - Поддержка динамического контента

3. **API JSON** - для открытых API
   - Wildberries
   - Высокая скорость и надежность

### Расписание парсинга

- **Ежедневно в 02:00** - полный парсинг всех магазинов
- **Каждые 6 часов** - обновление цен
- **По запросу** - обновление конкретного товара

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
docker-compose exec web_pricescan python manage.py test

# Конкретное приложение
docker-compose exec web_pricescan python manage.py test alerts

# С покрытием
docker-compose exec web_pricescan python -m pytest --cov=.
```

### Тестовые данные

```bash
# Загрузка тестовых данных
docker-compose exec web_pricescan python manage.py loaddata fixtures/test_data.json
```

## 🚀 Развертывание в продакшене

### Подготовка

1. **Настройте переменные окружения**
2. **Настройте SSL сертификаты**
3. **Настройте мониторинг (Prometheus + Grafana)**
4. **Настройте резервное копирование БД**

### Команды

```bash
# Сборка образов
docker-compose build

# Запуск в продакшене
docker-compose -f docker-compose.prod.yml up -d

# Миграции
docker-compose exec web_pricescan python manage.py migrate

# Сбор статических файлов
docker-compose exec web_pricescan python manage.py collectstatic --noinput
```

## 📈 Производительность

### Оптимизации

- **Индексы БД** для быстрого поиска
- **Кэширование** часто запрашиваемых данных
- **Пагинация** для больших списков
- **Rate limiting** для защиты от злоупотреблений
- **Асинхронные задачи** для тяжелых операций

### Масштабирование

- **Горизонтальное масштабирование** Celery workers
- **Кластеризация Redis** для высокой доступности
- **Read replicas** для PostgreSQL
- **CDN** для статических файлов

## 🤝 Разработка

### Структура проекта

```
pricescan/
├── pricescan_api/          # Django API
│   ├── alerts/             # Система алертов
│   ├── monitoring/         # Мониторинг
│   ├── parsers/           # Интеграция парсеров
│   ├── product/           # Продукты и предложения
│   └── user/              # Пользователи
├── pricescan_bot/         # Telegram бот
├── pricescan_parser/      # BS4 парсер
├── pricescan_playwright/  # Playwright парсер
└── nginx/                 # Nginx конфигурация
```

### Добавление нового парсера

1. Создайте новый модуль в `pricescan_parser/`
2. Реализуйте интерфейс парсера
3. Добавьте в `api_server.py`
4. Обновите конфигурацию в Django

### Добавление нового магазина

1. Создайте запись в модели `Shop`
2. Настройте парсер для магазина
3. Добавьте тестовые данные
4. Обновите документацию

## 📝 Лицензия

MIT License

## 👥 Автор

- **Куксин Дмитрий**

## 🙏 Благодарности

- Django Community
- aiogram Team
- Playwright Team
- BeautifulSoup Team

---

**PriceScan** - умный мониторинг цен для умных покупателей! 🛒💰