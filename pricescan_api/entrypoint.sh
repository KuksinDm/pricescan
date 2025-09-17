#!/bin/bash
set -e 
# Ждем, пока база данных будет доступна
echo "Waiting for database..."
sleep 5

# Создаем миграции
python manage.py makemigrations

# Выполняем миграции
python manage.py migrate

# Собираем статику
python manage.py collectstatic --noinput

# Копируем статику
echo "Copy static files..."
cp -r /app/collected_static/. /app/backend_static/

# Создаем суперпользователя
python manage.py createsuperuser --noinput \
    --username $DJANGO_SUPERUSER_USER \
    --email $DJANGO_SUPERUSER_EMAIL || {
        echo "Superuser already exists"
    }

# Импортируем данные
# python manage.py load_autors         || true
# python manage.py load_categories     || true
# python manage.py load_publishers     || true
# python manage.py load_products       || true
# python manage.py load_shops          || true
# python manage.py load_offers         || true
# python manage.py load_price_history  || true

exec gunicorn --bind 0.0.0.0:9040 config.wsgi:application
