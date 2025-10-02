from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import os
import re
from tempfile import gettempdir

app = FastAPI(title="Trendyol Review Scraper")

class ScrapeRequest(BaseModel):
    url: str

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-extensions")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scroll_to_load_all_reviews(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # scroll sonrası yüklenmesi için bekle
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def get_star_count(review):
    try:
        container = review.find_element(By.CLASS_NAME, "star-rating-star-container")
        full_star = container.find_element(By.CLASS_NAME, "star-rating-full-star")
        style = full_star.get_attribute("style")
        match = re.search(r'padding-inline-end:\s*([\d.]+)px', style)
        if match:
            padding = float(match.group(1))
            if padding < 1:
                return 5
            elif padding < 20:
                return 4
            elif padding < 37:
                return 3
            elif padding < 54:
                return 2
            elif padding < 71:
                return 1
            else:
                return 0
        else:
            return 5
    except:
        return 0

def scrape_reviews(url):
    driver = setup_driver()
    driver.get(url)
    time.sleep(3)
    scroll_to_load_all_reviews(driver)
    reviews_elements = driver.find_elements(By.CLASS_NAME, "review")
    reviews = []
    for r in reviews_elements:
        stars = get_star_count(r)
        if stars < 4:
            continue
        try:
            username = r.find_element(By.CSS_SELECTOR, ".review-info-detail .name").text.strip()
        except:
            username = ""
        try:
            date_container = r.find_element(By.CSS_SELECTOR, ".review-info-detail .date")
            spans = date_container.find_elements(By.TAG_NAME, "span")
            if len(spans) >= 3:
                date = f"{spans[0].text} {spans[1].text} {spans[2].text}"
            else:
                date = ""
        except:
            date = ""
        try:
            comment_div = r.find_element(By.CSS_SELECTOR, "div.review-comment")
            comment_span = comment_div.find_element(By.CSS_SELECTOR, "span.review-comment")
            comment = comment_span.text.strip()
        except:
            try:
                comment = r.find_element(By.CLASS_NAME, "review-comment").text.strip()
            except:
                comment = ""
        photos = []
        try:
            photo_container = r.find_element(By.CLASS_NAME, "review-media")
            img_elements = photo_container.find_elements(By.TAG_NAME, "img")
            for img in img_elements:
                url = img.get_attribute("src")
                if url:
                    url = url.replace("300/300", "1000/1000")
                    photos.append(url)
        except:
            pass
        if comment:
            reviews.append({
                "name": username,
                "comment": comment,
                "date": date,
                "stars": stars,
                "photos": photos
            })
    driver.quit()
    return reviews

def save_to_csv(reviews, product_name="urun"):
    temp_dir = gettempdir()
    filename = f"{product_name}_reviews.csv"
    filepath = os.path.join(temp_dir, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "comment", "date", "stars", "photos"])
        for r in reviews:
            writer.writerow([
                r["name"],
                r["comment"],
                r["date"],
                r["stars"],
                "; ".join(r["photos"])
            ])
    return filepath

@app.post("/scrape")
def scrape_endpoint(request: ScrapeRequest):
    try:
        reviews = scrape_reviews(request.url)
        if not reviews:
            return {"message": "Yorum bulunamadı"}
        filepath = save_to_csv(reviews, "trendyol")
        return {"reviews_count": len(reviews), "csv_path": filepath}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
