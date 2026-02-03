import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_google_maps(
    query: str,
    max_places: int = 10,
    lang: str = "en",
    headless: bool = True,
):
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

        try:
            await page.goto(search_url, timeout=120000)
            await page.wait_for_timeout(5000)
        except PlaywrightTimeoutError:
            logger.error("Page load timeout")
            await browser.close()
            return results

        # Прокрутка feed для подгрузки карточек
        try:
            feed = page.locator("div[role='feed']")
            for _ in range(max_places // 5 + 3):
                await feed.evaluate("el => el.scrollBy(0, el.scrollHeight)")
                await page.wait_for_timeout(2000)
        except Exception:
            logger.warning("Feed scroll failed")

        # Сбор карточек
        cards = page.locator("a[aria-label][href*='/maps/place/']")
        count = min(await cards.count(), max_places)
        logger.info(f"Found {count} places")

        for i in range(count):
            try:
                await cards.nth(i).click()
                await page.wait_for_timeout(3000)

                place = {}

                try:
                    place["name"] = await page.locator("h1").inner_text()
                except:
                    place["name"] = None

                try:
                    rating_text = await page.locator("span[aria-hidden='true']").first.inner_text()
                    place["rating"] = float(rating_text.replace(",", "."))
                except:
                    place["rating"] = None

                try:
                    place["address"] = await page.locator("button[data-item-id='address']").inner_text()
                except:
                    place["address"] = None

                place["google_maps_url"] = page.url
                results.append(place)
                logger.info(f"✓ {i+1}/{count}: {place.get('name')}")

            except Exception as e:
                logger.warning(f"Skipped {i+1}: {e}")

        await browser.close()
    return results
