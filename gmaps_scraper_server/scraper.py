import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_google_maps(
    query: str,
    max_places: int = 10,
    lang: str = "en",
    headless: bool = True,
):
    """
    Async scraper Google Maps с актуальными селекторами карточек.
    """
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
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

        # Находим карточки мест по новым селекторам
        cards = page.locator("a.hfpxzc[aria-label]")  # актуальный селектор
        count = min(await cards.count(), max_places)
        logger.info(f"Found {count} places")

        for i in range(count):
            try:
                place = {}
                place["name"] = await cards.nth(i).get_attribute("aria-label")
                place["google_maps_url"] = await cards.nth(i).get_attribute("href")
                # Можно оставить рейтинг и адрес None — если потребуется, можно искать по новой логике
                place["rating"] = None
                place["address"] = None
                results.append(place)
                logger.info(f"✓ {i+1}/{count}: {place.get('name')}")
            except Exception as e:
                logger.warning(f"Skipped {i+1}: {e}")

        await browser.close()
    return results
