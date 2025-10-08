# Базовый образ Ubuntu с Python
FROM python:3.12-slim

# Рабочая директория
WORKDIR /app

# Копируем файлы проекта
COPY pyproject.toml uv.lock ./


# Устанавливаем зависимости
RUN pip install uv
RUN uv pip install --system .

COPY . .

CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
