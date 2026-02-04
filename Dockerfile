# Используем официальный Python образ
FROM python:3.10-slim

LABEL maintainer="QR Code Flask Application"
LABEL description="Flask приложение для генерации QR-кодов"

RUN apt-get update && apt-get install -y libzbar0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

COPY . .

# Создаем директории
RUN mkdir -p uploads static/media instance storage && \
    chmod -R 755 uploads static/media instance storage

# Запускаем от root для упрощения (простой проект, не требует повышенной безопасности)

EXPOSE 5000
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/login')" || exit 1

# Команда запуска теперь в docker-compose.yml
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "120", "app:app"]