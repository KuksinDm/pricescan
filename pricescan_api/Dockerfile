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

# Делаем entrypoint.sh исполняемым
RUN chmod +x entrypoint.sh

# Запускаем сервер через entrypoint.sh
CMD ["./entrypoint.sh"]