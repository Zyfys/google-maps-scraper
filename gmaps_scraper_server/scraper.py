from playwright.sync_api import sync_playwright
import time
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_google_maps(
    query: str,
    max_places: int = 10,
    lang: str = "en",
    headless: bool = True,
):
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = browser.new_context(
            locale=lang,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()

        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}?hl={lang}"
        logger.info(f"Opening: {search_url}")
        page.goto(search_url, timeout=60000)

        page.wait_for_timeout(5000)

        # Скроллим список результатов
        try:
            scrollable = page.locator("div[role='feed']")
            for _ in range(max_places // 5 + 2):
                scrollable.evaluate("el => el.scrollBy(0, el.scrollHeight)")
                page.wait_for_timeout(1500)
        except:
            logger.warning("Could not scroll results list")

        cards = page.locator("a[href*='/maps/place/']")
        count = min(cards.count(), max_places)

        logger.info(f"Found {count} places")

        for i in range(count):
            try:
                cards.nth(i).click()
                page.wait_for_timeout(3000)

                place = {}

                # Название
                try:
                    place["name"] = page.locator("h1").inner_text()
                except:
                    place["name"] = None

                # Рейтинг
                try:
                    rating_text = page.locator("span[aria-hidden='true']").first.inner_text()
                    place["rating"] = float(rating_text.replace(",", "."))
                except:
                    place["rating"] = None

                # Адрес
                try:
                    place["address"] = page.locator("button[data-item-id='address']").inner_text()
                except:
                    place["address"] = None

                place["google_maps_url"] = page.url

                results.append(place)
                logger.info(f"✓ {i+1}/{count}: {place.get('name')}")

            except Exception as e:
                logger.warning(f"Skipped place {i+1}: {e}")
                continue

        browser.close()

    return results
