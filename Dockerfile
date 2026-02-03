FROM python:3.10-slim

# Устанавливаем системные зависимости для Playwright и xvfb
RUN apt-get update && apt-get install -y \
    wget curl gnupg git xvfb libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1 \
    libxrandr2 libxdamage1 libxkbcommon0 libpango-1.0-0 libgtk-3-0 libgbm-dev \
    libasound2 libxshmfence1 fonts-liberation --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем python-зависимости
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Playwright и скачиваем браузеры
RUN pip install playwright && playwright install

# Копируем проект
COPY . .

# Экспорт переменной окружения для xvfb
ENV DISPLAY=:99

# Запуск через xvfb-run, чтобы headful браузер работал
CMD ["xvfb-run", "-s", "-screen 0 1920x1080x24", "uvicorn", "gmaps_scraper_server.main_api:app", "--host", "0.0.0.0", "--port", "8001"]
