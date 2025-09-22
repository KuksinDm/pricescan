FROM python:3.12-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Установка Playwright
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Установка зависимостей
RUN pip install uv && uv pip install --system .

# Копирование исходного кода
COPY . .

# Открытие порта
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
