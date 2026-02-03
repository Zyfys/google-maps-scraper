import asyncio
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
            await page.goto(search_url, timeout=60000)
            # Ждём появления карточек
            await page.wait_for_selector("a[aria-label][href*='/maps/place/']", timeout=30000)
        except Exception as e:
            logger.error(f"Page load or selector timeout: {e}")
            await browser.close()
            return results

        # Скроллим список с логированием
        try:
            feed = page.locator("div[role='feed']")
            for _ in range(max_places // 5 + 2):
                await feed.evaluate("el => el.scrollBy(0, el.scrollHeight)")
                await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning(f"Feed scroll failed: {e}")

        # Собираем карточки
        cards = page.locator("a[href*='/maps/place/']")
        count = min(await cards.count(), max_places)
        logger.info(f"Found {count} places")

        for i in range(count):
            try:
                await cards.nth(i).click()
                await page.wait_for_timeout(3000)

                place = {}
                # Имя
                try:
                    place["name"] = await page.locator("h1").inner_text()
                except:
                    place["name"] = None
                # Рейтинг
                try:
                    rating_text = await page.locator("span[aria-hidden='true']").first.inner_text()
                    place["rating"] = float(rating_text.replace(",", "."))
                except:
                    place["rating"] = None
                # Адрес
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

# Пример локального теста
if __name__ == "__main__":
    query = "Restaurant Batumi"
    res = asyncio.run(scrape_google_maps(query, max_places=5, lang="en", headless=True))
    print(res)
