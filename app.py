from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
from fastapi.responses import FileResponse

@app.get("/")
def home():
    return FileResponse("index.html")


app = FastAPI(title="Trendyol Yorum Çekme Demo")

# Basit yorum cache
yorum_cache = {}

def get_trendyol_comments(shop_url: str):
    if shop_url in yorum_cache:
        return yorum_cache[shop_url]

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(shop_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return [f"Hata: {e}"]

    soup = BeautifulSoup(resp.text, "html.parser")
    # Trendyol yorumları için örnek selector (gerçek siteye göre değişebilir)
    yorumlar = [c.get_text(strip=True) for c in soup.select(".review-text")]

    if not yorumlar:
        yorumlar = ["Yorum bulunamadı veya selector değişti."]

    yorum_cache[shop_url] = yorumlar
    return yorumlar

@app.get("/yorumlar")
def yorumlar(shop: str = Query(..., description="Trendyol mağaza URL")):
    comments = get_trendyol_comments(shop)
    return {"shop": shop, "yorumlar": comments}

@app.get("/generate")
def generate_embed(shop: str = Query(..., description="Trendyol mağaza URL")):
    comments = get_trendyol_comments(shop)
    # Embed kodu (iframe)
    # iframe src, FastAPI embed endpoint'ini çağıracak
    embed_code = f'<iframe src="https://<RENDER_APP_URL>/embed?shop={shop}" width="400" height="600"></iframe>'
    return {"embed": embed_code, "yorum_sayisi": len(comments)}

@app.get("/embed")
def embed(shop: str = Query(...)):
    comments = get_trendyol_comments(shop)
    html = "<ul>" + "".join([f"<li>{c}</li>" for c in comments]) + "</ul>"
    return HTMLResponse(f"<div>{html}</div>")
