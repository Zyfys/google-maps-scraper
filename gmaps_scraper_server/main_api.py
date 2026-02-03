import logging
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# Попробуем импортировать scraper
try:
    from gmaps_scraper_server.scraper import scrape_google_maps
except ImportError:
    logging.error("Could not import scrape_google_maps from scraper.py")
    # Заглушка, чтобы API запускалось, но падало при вызове
    async def scrape_google_maps(*args, **kwargs):
        raise ImportError("Scraper function not available.")

app = FastAPI(title="Google Maps Scraper API")

# Разрешаем CORS, чтобы n8n могла делать запросы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/scrape-get")
async def scrape_get(
    query: str = Query(..., description="Search query for Google Maps"),
    max_places: int = Query(10, description="Maximum number of places to return"),
    lang: str = Query("en", description="Language code for Google Maps"),
    headless: bool = Query(True, description="Run browser in headless mode"),
):
    """
    Endpoint для n8n / внешних клиентов.
    Возвращает список мест из Google Maps по запросу.
    """
    try:
        results = await scrape_google_maps(query, max_places, lang, headless)
        return {"success": True, "count": len(results), "results": results}
    except Exception as e:
        logging.exception("Error in scrape_get:")
        return {"success": False, "error": str(e)}
