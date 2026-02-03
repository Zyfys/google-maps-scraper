print("LOADED SCRAPER.PY FROM:", __file__)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_google_maps(query: str, max_places: int = 20, lang: str = "en", headless: bool = True):
    """
    Scrape Google Maps for places based on search query
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"--lang={lang}")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    results = []
    
    try:
        # Формируем URL для поиска
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}?hl={lang}"
        logger.info(f"Navigating to: {search_url}")
        driver.get(search_url)
        
        # Ждем загрузки страницы
        time.sleep(5)
        
        # Пытаемся найти и принять cookies (если появляется)
        try:
            consent_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept') or contains(., 'Reject') or contains(., 'Принять')]"))
            )
            consent_button.click()
            logger.info("Accepted consent")
            time.sleep(2)
        except:
            logger.info("No consent dialog or already accepted")
        
        # Пробуем несколько селекторов для поиска списка результатов
        feed_selectors = [
            "div[role='feed']",
            "div[role='main']",
            ".m6QErb.DxyBCb.kA9KIf.dS8AEf",
            "div[aria-label*='Results']",
            "div.m6QErb"
        ]
        
        scrollable_div = None
        for selector in feed_selectors:
            try:
                scrollable_div = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logger.info(f"Found feed element with selector: {selector}")
                break
            except:
                continue
        
        if not scrollable_div:
            logger.error("Could not find results container")
            # Сохраняем скриншот для отладки
            driver.save_screenshot("/tmp/gmaps_error.png")
            logger.error("Screenshot saved to /tmp/gmaps_error.png")
            return results
        
        # Прокручиваем для загрузки всех результатов
        logger.info("Scrolling to load more results...")
        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
        
        for scroll_attempt in range(max_places // 10 + 2):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(2)
            
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            if new_height == last_height:
                break
            last_height = new_height
        
        # Ищем элементы мест с разными селекторами
        place_selectors = [
            "a[href*='/maps/place/']",
            "div.Nv2PK a",
            "a.hfpxzc",
            "div[role='article'] a"
        ]
        
        places = []
        for selector in place_selectors:
            try:
                places = driver.find_elements(By.CSS_SELECTOR, selector)
                if places:
                    logger.info(f"Found {len(places)} places with selector: {selector}")
                    break
            except:
                continue
        
        if not places:
            logger.error("No place elements found")
            driver.save_screenshot("/tmp/gmaps_no_places.png")
            return results
        
        logger.info(f"Processing up to {min(len(places), max_places)} places...")
        
        for idx, place in enumerate(places[:max_places]):
            try:
                # Кликаем на место
                driver.execute_script("arguments[0].scrollIntoView(true);", place)
                time.sleep(1)
                place.click()
                time.sleep(3)
                
                place_data = {}
                
                # Название
                try:
                    name_selectors = ["h1.DUwDvf", "h1", "h2.qBF1Pd"]
                    for sel in name_selectors:
                        try:
                            place_data['name'] = driver.find_element(By.CSS_SELECTOR, sel).text
                            if place_data['name']:
                                break
                        except:
                            continue
                    if not place_data.get('name'):
                        place_data['name'] = "N/A"
                except:
                    place_data['name'] = "N/A"
                
                # Рейтинг
                try:
                    rating_selectors = [
                        "div.F7nice span[aria-hidden='true']",
                        "span.ceNzKf[aria-hidden='true']",
                        "div[jsaction*='rating'] span"
                    ]
                    for sel in rating_selectors:
                        try:
                            rating_text = driver.find_element(By.CSS_SELECTOR, sel).text
                            place_data['rating'] = float(rating_text.replace(',', '.'))
                            break
                        except:
                            continue
                    if 'rating' not in place_data:
                        place_data['rating'] = None
                except:
                    place_data['rating'] = None
                
                # Количество отзывов
                try:
                    reviews_selectors = [
                        "div.F7nice span:nth-of-type(2)",
                        "button[aria-label*='reviews'] span",
                        "span.RDApEe"
                    ]
                    for sel in reviews_selectors:
                        try:
                            reviews_text = driver.find_element(By.CSS_SELECTOR, sel).text
                            reviews_match = re.search(r'[\d,]+', reviews_text.replace(',', ''))
                            if reviews_match:
                                place_data['reviews_count'] = int(reviews_match.group())
                                break
                        except:
                            continue
                    if 'reviews_count' not in place_data:
                        place_data['reviews_count'] = 0
                except:
                    place_data['reviews_count'] = 0
                
                # Адрес
                try:
                    address_selectors = [
                        "button[data-item-id='address']",
                        "button[data-tooltip='Copy address']",
                        "div.rogA2c div"
                    ]
                    for sel in address_selectors:
                        try:
                            place_data['address'] = driver.find_element(By.CSS_SELECTOR, sel).get_attribute('aria-label') or \
                                                   driver.find_element(By.CSS_SELECTOR, sel).text
                            if place_data['address']:
                                break
                        except:
                            continue
                    if not place_data.get('address'):
                        place_data['address'] = "N/A"
                except:
                    place_data['address'] = "N/A"
                
                # Веб-сайт
                try:
                    website_selectors = [
                        "a[data-item-id='authority']",
                        "a[href^='http'][data-item-id*='authority']",
                        "a.CsEnBe[href^='http']"
                    ]
                    for sel in website_selectors:
                        try:
                            place_data['website'] = driver.find_element(By.CSS_SELECTOR, sel).get_attribute('href')
                            if place_data['website'] and 'google.com' not in place_data['website']:
                                break
                        except:
                            continue
                    if not place_data.get('website'):
                        place_data['website'] = None
                except:
                    place_data['website'] = None
                
                # Телефон
                try:
                    phone_selectors = [
                        "button[data-item-id*='phone']",
                        "button[aria-label*='Phone']",
                        "button.CsEnBe[aria-label*='+']"
                    ]
                    for sel in phone_selectors:
                        try:
                            phone_elem = driver.find_element(By.CSS_SELECTOR, sel)
                            place_data['phone'] = phone_elem.get_attribute('aria-label') or phone_elem.text
                            if place_data['phone']:
                                # Очищаем от лишнего текста
                                phone_match = re.search(r'[\d\s\+\-\(\)]+', place_data['phone'])
                                if phone_match:
                                    place_data['phone'] = phone_match.group().strip()
                                break
                        except:
                            continue
                    if not place_data.get('phone'):
                        place_data['phone'] = None
                except:
                    place_data['phone'] = None
                
                # URL Google Maps
                place_data['google_maps_link'] = driver.current_url
                
                # Place ID из URL
                try:
                    place_id_match = re.search(r'!1s([^!]+)', driver.current_url)
                    place_data['place_id'] = place_id_match.group(1) if place_id_match else None
                except:
                    place_data['place_id'] = None
                
                # Координаты из URL
                try:
                    coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', driver.current_url)
                    if coords_match:
                        place_data['latitude'] = float(coords_match.group(1))
                        place_data['longitude'] = float(coords_match.group(2))
                    else:
                        place_data['latitude'] = None
                        place_data['longitude'] = None
                except:
                    place_data['latitude'] = None
                    place_data['longitude'] = None
                
                # Категории
                try:
                    categories_selectors = [
                        "button[jsaction*='category']",
                        "button.DkEaL",
                        "span.YhemCb"
                    ]
                    categories = []
                    for sel in categories_selectors:
                        try:
                            cat_elements = driver.find_elements(By.CSS_SELECTOR, sel)
                            categories = [cat.text for cat in cat_elements if cat.text]
                            if categories:
                                break
                        except:
                            continue
                    place_data['categories'] = categories
                except:
                    place_data['categories'] = []
                
                # Фото (URL первых нескольких фото)
                try:
                    photo_urls = []
                    photo_buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Photo']")[:5]
                    
                    for photo_btn in photo_buttons:
                        try:
                            # Ищем изображение внутри кнопки
                            img = photo_btn.find_element(By.CSS_SELECTOR, "img")
                            photo_url = img.get_attribute('src')
                            
                            # Преобразуем URL для получения большого размера
                            if photo_url and 'googleusercontent' in photo_url:
                                # Убираем параметры размера и добавляем свои
                                photo_url = re.sub(r'=w\d+-h\d+', '=w1600', photo_url)
                                photo_urls.append(photo_url)
                        except:
                            continue
                    
                    place_data['photos'] = photo_urls
                    place_data['main_photo'] = photo_urls[0] if photo_urls else None
                    place_data['photos_count'] = len(photo_urls)
                except Exception as e:
                    logger.warning(f"Could not extract photos: {e}")
                    place_data['photos'] = []
                    place_data['main_photo'] = None
                    place_data['photos_count'] = 0
                
                results.append(place_data)
                logger.info(f"✓ Scraped {idx + 1}/{max_places}: {place_data['name']}")
                
            except Exception as e:
                logger.error(f"Error scraping place {idx + 1}: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"Fatal error during scraping: {str(e)}")
    finally:
        driver.quit()
    
    return results
