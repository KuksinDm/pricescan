# Базовый образ Ubuntu с Python
FROM python:3.12-slim

# Устанавливаем системные зависимости для Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем только pyproject.toml (без uv.lock)
COPY pyproject.toml ./

# Устанавливаем uv
RUN pip install uv

# Устанавливаем зависимости через uv
RUN uv pip install --system .

# Устанавливаем Playwright браузеры
RUN playwright install chromium
RUN playwright install-deps

# Копируем исходный код
COPY . .

# Запускаем приложение
CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]