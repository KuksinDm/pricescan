FROM python:3.12-slim

WORKDIR /app

# только манифесты
COPY pyproject.toml uv.lock ./
RUN pip install -U pip uv && uv pip install --system .

# пакет целиком в подпапку
COPY . /app/pricescan_bot


CMD ["python", "-m", "pricescan_bot.main"]