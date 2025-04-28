import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

# Konfigurasi SerpApi
SERPAPI_API_KEY = "ebfdf596fb90e281a6b40f92a1b51b03558a17e2ea2b2cd4babf842712831f4a"
QUERIES = ["ptpn v", "PTPN IV REGIONAL III", "PTPN V", "PTPN IV","PT Perkebunan Nusantara V"]
SERPAPI_URL = "https://serpapi.com/search"

# Fungsi untuk mengubah format tanggal
def convert_date(raw_date):
    try:
        date_obj = datetime.strptime(raw_date, "%m/%d/%Y, %I:%M %p, %z UTC")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        return "0000-00-00"

# Fungsi untuk cek apakah berita adalah berita hari ini
def is_today(news_date, target_date):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return news_date == target_date

# Fungsi untuk mengambil isi berita dari link
def get_news_content(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        meta_title = soup.title.string.strip() if soup.title else "Title tidak ditemukan"
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_description = meta_desc_tag["content"].strip() if meta_desc_tag else "Deskripsi tidak ditemukan"

        return {
            "meta_title": meta_title,
            "meta_description": meta_description
        }
    except requests.exceptions.RequestException as e:
        print(f"Error scraping {url}: {e}")
        return {"meta_title": "Error", "meta_description": "Error"}

# Fungsi untuk mengambil berita dari SerpApi
def get_news(data):
    target_date = data.get("tanggal", datetime.utcnow().strftime("%Y-%m-%d"))
    all_news = []
    for query in QUERIES:
        print(f"Mengambil berita untuk query: {query}...")
        params = {
            "engine": "google_news",
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "location_requested": "Riau, Indonesia",
            "location_used": "Riau, Indonesia",
            "google_domain": "google.co.id",
            "hl": "id",
            "gl": "id",
            "tbs": f"cdr:1,cd_min:{target_date},cd_max:{target_date}"
        }

        try:
            response = requests.get(SERPAPI_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            news = data.get("news_results", [])

            for item in news:
                raw_date = item.get("date", "")
                formatted_date = convert_date(raw_date)

                # Hanya simpan berita hari ini
                if is_today(formatted_date, target_date):
                    link = item.get("link", "")
                    content_data = get_news_content(link) if link.startswith("http") else {"meta_title": "Tidak ada", "meta_description": "Tidak ada"}

                    all_news.append({
                        "title": item.get("title", ""),
                        "date": formatted_date,
                        "source": item.get("source", "Tidak diketahui"),
                        "link": link,
                        "meta_title": content_data["meta_title"],
                        "meta_description": content_data["meta_description"]
                    })

        except requests.exceptions.RequestException as e:
            print(f"Error mengambil berita untuk '{query}': {e}")

    return all_news