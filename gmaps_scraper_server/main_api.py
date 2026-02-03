import logging
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from gmaps_scraper_server.scraper import scrape_google_maps  # импорт твоего обновлённого scraper.py

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Google Maps Scraper API",
    description="Async FastAPI service for scraping Google Maps data. Works with n8n.",
    version="1.0.0",
)

# CORS для внешних запросов (например, n8n)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Google Maps Scraper API is running"}

@app.get("/scrape-get")
async def scrape_get(
    query: str = Query(..., description="Search query, e.g., 'hotels in Batumi'"),
    max_places: int = Query(10, description="Maximum number of results"),
    lang: str = Query("en", description="Language code for results"),
    headless: bool = Query(True, description="Run browser in headless mode"),
):
    """
    Scrape Google Maps for places based on the search query.
    Returns a JSON with results.
    """
    logger.info(f"Scrape request: query='{query}', max_places={max_places}, lang='{lang}', headless={headless}")
    try:
        results = await scrape_google_maps(query, max_places, lang, headless)
        return {
            "success": True,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Scrape failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": []
        }
