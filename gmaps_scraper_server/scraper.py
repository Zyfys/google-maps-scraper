import asyncio
import logging
import glob as _glob
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scrape_google_maps(
    query: str,
    max_places: int = 10,
    lang: str = "en",
    headless: bool = True,
    min_reviews: int = 0,
    delay_seconds: float = 3.0,
):
    results = []

    _chrome_paths = _glob.glob("/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome")
    _exec = _chrome_paths[0] if _chrome_paths else None

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            executable_path=_exec,
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
            await page.wait_for_selector("a[aria-label][href*='/maps/place/']", timeout=30000)
        except Exception as e:
            logger.error(f"Page load or selector timeout: {e}")
            await browser.close()
            return results

        # Scroll to load more places
        try:
            feed = page.locator("div[role='feed']")
            scroll_rounds = max_places // 5 + 3
            for _ in range(scroll_rounds):
                await feed.evaluate("el => el.scrollBy(0, el.scrollHeight)")
                await page.wait_for_timeout(1500)
        except Exception as e:
            logger.warning(f"Feed scroll failed: {e}")

        cards = page.locator("a[href*='/maps/place/']")
        count = min(await cards.count(), max_places * 2)  # grab extra to account for filtered ones
        logger.info(f"Found {count} cards, will collect up to {max_places} (min_reviews={min_reviews})")

        collected = 0
        for i in range(count):
            if collected >= max_places:
                break
            try:
                await cards.nth(i).click()
                await page.wait_for_timeout(int(delay_seconds * 1000))

                place = {}

                # Name
                try:
                    place["name"] = await page.locator("h1").first.inner_text(timeout=5000)
                except:
                    place["name"] = None

                # Rating
                try:
                    rating_el = page.locator("div[jsaction] span[aria-hidden='true']").first
                    rating_text = await rating_el.inner_text(timeout=3000)
                    place["rating"] = float(rating_text.replace(",", "."))
                except:
                    place["rating"] = None

                # Reviews count
                try:
                    reviews_el = page.locator("span[aria-label*='отзыв'], span[aria-label*='review'], button[jsaction*='pane.rating']")
                    reviews_text = await reviews_el.first.get_attribute("aria-label", timeout=3000)
                    if reviews_text:
                        import re
                        nums = re.findall(r"[\d\s,]+", reviews_text.replace("\xa0", ""))
                        if nums:
                            place["reviews_count"] = int(nums[0].replace(",", "").replace(" ", "").strip())
                        else:
                            place["reviews_count"] = None
                    else:
                        place["reviews_count"] = None
                except:
                    place["reviews_count"] = None

                # Filter by min_reviews
                if min_reviews > 0:
                    rc = place.get("reviews_count") or 0
                    if rc < min_reviews:
                        logger.info(f"  Skip '{place.get('name')}' — reviews {rc} < {min_reviews}")
                        continue

                # Address
                try:
                    place["address"] = await page.locator("button[data-item-id='address']").inner_text(timeout=3000)
                except:
                    place["address"] = None

                # Phone
                try:
                    phone_btn = page.locator("button[data-item-id*='phone']")
                    place["phone"] = await phone_btn.first.get_attribute("data-item-id", timeout=3000)
                    if place["phone"] and place["phone"].startswith("phone:"):
                        place["phone"] = place["phone"].replace("phone:", "")
                    else:
                        place["phone"] = await phone_btn.first.inner_text(timeout=2000)
                except:
                    place["phone"] = None

                # Website
                try:
                    place["website"] = await page.locator("a[data-item-id='authority']").get_attribute("href", timeout=3000)
                except:
                    place["website"] = None

                # Coordinates from URL
                try:
                    url = page.url
                    import re
                    coords = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
                    if coords:
                        place["latitude"] = float(coords.group(1))
                        place["longitude"] = float(coords.group(2))
                    else:
                        place["latitude"] = None
                        place["longitude"] = None
                except:
                    place["latitude"] = None
                    place["longitude"] = None

                # Categories
                try:
                    cat_el = page.locator("button[jsaction*='category']")
                    cats = []
                    for j in range(await cat_el.count()):
                        cats.append(await cat_el.nth(j).inner_text(timeout=1000))
                    place["categories"] = cats if cats else None
                except:
                    place["categories"] = None

                place["google_maps_url"] = page.url
                place["query"] = query
                results.append(place)
                collected += 1
                logger.info(f"✓ {collected}/{max_places}: {place.get('name')} | rating={place.get('rating')} | reviews={place.get('reviews_count')}")

            except Exception as e:
                logger.warning(f"Skipped card {i+1}: {e}")

        await browser.close()

    return results


if __name__ == "__main__":
    query = "Restaurants Tbilisi"
    res = asyncio.run(scrape_google_maps(query, max_places=5, lang="en", headless=True, min_reviews=100))
    import json
    print(json.dumps(res, ensure_ascii=False, indent=2))
