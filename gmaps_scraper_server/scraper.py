import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_google_maps(
    query: str,
    max_places: int = 10,
    lang: str = "en",
    headless: bool = True,  # всегда True для сервера
):
    """
    Рабочий async scraper Google Maps для headless сервера.
    Возвращает список мест с названием и ссылкой.
    """
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process"
            ],
        )

        context = await browser.new_context(
            locale=lang,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        page = await context.new_page()

        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}?hl={lang}"
        logger.info(f"Opening: {search_url}")
        await page.goto(search_url, timeout=60000)
        await page.wait_for_timeout(5000)

        # Найти карточки мест по актуальному селектору
        cards = page.locator("a[aria-label][href*='/maps/place/']")
        count = min(await cards.count(), max_places)
        logger.info(f"Found {count} places")

        for i in range(count):
            try:
                place = {}
                place["name"] = await cards.nth(i).get_attribute("aria-label")
                place["google_maps_url"] = await cards.nth(i).get_attribute("href")
                place["rating"] = None    # Можно добавить логику поиска рейтинга
                place["address"] = None   # Можно добавить логику поиска адреса
                results.append(place)
                logger.info(f"✓ {i+1}/{count}: {place.get('name')}")
            except Exception as e:
                logger.warning(f"Skipped {i+1}: {e}")

        await browser.close()
    return results
