import requests
import datetime
from bs4 import BeautifulSoup

# Konfigurasi SerpApi
SERPAPI_API_KEY = "f001362f93dea450ed85f03985ffaf34db4d48537b2e8172d04132cddde73710"
QUERIES = ["mudik","prabowo"]
SERPAPI_URL = "https://serpapi.com/search"

# Ambil tanggal hari ini
TODAY = datetime.date.today()

# Fungsi untuk mengambil berita dari SerpApi
def get_news():
    all_news = []
    
    for query in QUERIES:
        print("Debugging: Queries saat ini adalah", QUERIES)
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
            "tbs": "qdr:w"  # Hanya ambil berita dalam 24 jam terakhir
        }

        try:
            response = requests.get(SERPAPI_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            print(response.json())
            news = data.get("news_results", [])
            for item in news:
                raw_date = item.get("date", "")

                # Konversi tanggal ke format YYYY-MM-DD
                parsed_date = parse_date(raw_date)
                print(f"Raw date: {raw_date}, Parsed date: {parsed_date}")
                if parsed_date != TODAY:  
                    
                    continue  # Skip berita yang bukan dari hari ini

                link = item.get("link", "")
                if link.startswith("http"):
                    print(f"Scraping: {link}")
                    content_data = get_news_content(link)
                    item["meta_title"] = content_data["meta_title"]
                    item["meta_description"] = content_data["meta_description"]
                else:
                    item["meta_title"] = "Tidak ada"
                    item["meta_description"] = "Tidak ada"

                item["date"] = str(parsed_date)
                all_news.append(item)

        except requests.exceptions.RequestException as e:
            print(f"Error mengambil berita untuk '{query}': {e}")

    return all_news

# Fungsi untuk mengubah tanggal ke format YYYY-MM-DD
def parse_date(date_str):
    if "jam yang lalu" in date_str or "menit yang lalu" in date_str:
        return TODAY  # Jika berita baru beberapa jam/menit yang lalu, asumsikan hari ini
    elif "hari yang lalu" in date_str:
        num_days = int(date_str.split()[0])
        return TODAY - datetime.timedelta(days=num_days)
    else:
        try:
            return datetime.datetime.strptime(date_str, "%d %B %Y").date()
        except ValueError:
            return TODAY  # Default ke hari ini jika parsing gagal

# Fungsi untuk scraping meta title & meta description
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
        print(f"Error saat scraping {url}: {e}")
        return {
            "meta_title": "Error",
            "meta_description": "Error"
        }
