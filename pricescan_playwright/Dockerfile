# Базовый образ Ubuntu с Python
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

# Рабочая директория
WORKDIR /app

# ставим deps по lock-файлу (фиксация версий)
COPY pyproject.toml uv.lock ./
RUN pip install -U pip uv && uv pip install --system .

# Копируем исходный код
COPY . .

# Запускаем приложение
CMD ["python","-m","uvicorn","api_server:app","--host","0.0.0.0","--port","8000"]
