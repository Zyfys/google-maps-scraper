from fastapi import FastAPI
from gmaps_scraper_server.scraper import scrape_google_maps  # async scraper

# Создаем приложение FastAPI
app = FastAPI(title="Google Maps Scraper API")

@app.get("/scrape-get")
async def scrape_get(
    query: str,           # поисковый запрос
    max_places: int = 10, # максимум результатов
    lang: str = "en",     # язык интерфейса
    headless: bool = True # запуск браузера в фоновом режиме
):
    """
    Async endpoint для скрапинга Google Maps.
    
    Использует async Playwright, полностью совместимо с FastAPI.
    """
    # Вызов асинхронного scraper
    results = await scrape_google_maps(query, max_places, lang, headless)
    return results

# ===========================
# Пример запуска через uvicorn:
# uvicorn gmaps_scraper_server.main_api:app --reload --port 8000
# ===========================
