import requests
from bs4 import BeautifulSoup

url = "https://ejurnal.seminar-id.com/index.php/tin"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

response = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(response.text, "html.parser")
print(soup.get_text(separator="\n", strip=True)[:3000])