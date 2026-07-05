import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ============================================================
# 1. AMBIL RAW TEXT & SOUP DARI HALAMAN
# ============================================================
def get_page(url):
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup, soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"  ERROR akses {url}: {e}")
        return None, ""


# ============================================================
# 2. EKSTRAK INFO DASAR
# ============================================================
def extract_info(raw_text):
    result = {
        "journal":   None,
        "sinta":     None,
        "pissn":     None,
        "eissn":     None,
        "frequency": None,
        "publisher": None,
        "apc":       None,
    }

    # --- Nama jurnal (format tabel) ---
    for pattern in [
        r"Journal title\s*:\s*(.+)",
        r"Jornal Name\s*:\s*(.+)",
        r"Journal Name\s*:\s*(.+)",
    ]:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            result["journal"] = match.group(1).strip()
            break

    # Format paragraf
    if not result["journal"]:
        for pattern in [
            r"^(.+?)\nis a (?:scientific|peer-reviewed|Journal)",
            r"^(.+?)\nMain Navigation",
        ]:
            match = re.search(pattern, raw_text, re.MULTILINE)
            if match:
                result["journal"] = match.group(1).strip()
                break

    # --- SINTA ---
        for pattern in [
            r"Accredited\s*:\s*(Sinta \d+)",
            r"ACCREDITED\s+(SINTA \d+)",
            r"SINTA rating of\s*(\d+)",
            r"reAccreditation.+?SINTA.+?(\d+)",
            r"Accredited Rank\s*(\d+)",
            r"Rank\s+(\d+)\s+SINTA",
            r"upgraded.+?Sinta\s*(\d+)",
            r"Sinta\s*(\d+).+?(?:2025|2026|2027|2028|2029|2030)",
        ]:
            match = re.search(pattern, raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                num = re.search(r"\d+", match.group(1))
                if num:
                    result["sinta"] = f"Sinta {num.group()}"
                    break

        # Prioritas 2: fallback kalau belum ketemu
        if not result["sinta"]:
            match = re.search(r"(Sinta \d+)", raw_text, re.IGNORECASE)
            if match:
                num = re.search(r"\d+", match.group(1))
                if num:
                    result["sinta"] = f"Sinta {num.group()}"

    # --- P-ISSN ---
    for pattern in [
        r"P-ISSN\s*[:\|]?\s*([\d-]+)",
        r"ISSN\s*\(Printed\)\s*[:\|]?\s*([\d-]+)",
        r"p-ISSN\s*[:\|]?\s*([\d-]+)",
        r"P-ISSN\s*:\s*([\d-]+)",
    ]:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            result["pissn"] = match.group(1).strip()
            break

    # --- E-ISSN ---
    for pattern in [
        r"E-ISSN\s*[:\|]?\s*([\d-]+)",
        r"ISSN\s*\(Online\)\s*[:\|]?\s*([\d-]+)",
        r"e-ISSN\s*[:\|]?\s*([\d-]+)",
        r"e\s*-\s*ISSN\s*:\s*([\d-]+)",
    ]:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            result["eissn"] = match.group(1).strip()
            break

    # --- Frekuensi terbit ---
    for pattern in [
        r"Frequency\s*[:\|]?\s*(.+?)(?:\n|$)",
        r"Frequency of Publication\s*[:\|]?\s*(.+?)(?:\n|$)",
        r"Issued Frequency\s*(.+?)\.",
        r"published.+?(\d+\s*(?:times?|editions?|issues?).+?)(?:\.|$)",
    ]:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            result["frequency"] = match.group(1).strip()
            break

    # --- Publisher ---
    for pattern in [
        r"Publisher\s*:\s*(.+)",
        r"published by\s+(.+?)[,.\n]",
        r"Publisher\n(.+)",
    ]:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            result["publisher"] = match.group(1).strip()
            break

    # --- APC di halaman utama ---
    result["apc"] = extract_apc(raw_text)

    return result


# ============================================================
# 3. EKSTRAK APC DARI RAW TEXT
# ============================================================
def extract_apc(raw_text):
    hasil = []

    # Ambil semua nominal IDR (skip yang 0)
    # Handle format: 1.000.000 (IDR), IDR 1,500,000, Rp. 400.000,-
    for match in re.finditer(
        r"([\d]{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|\d+)\s*\(IDR\)|IDR\s*([\d,. ]+)|Rp\.?\s*([\d.,]+)",
        raw_text, re.IGNORECASE
    ):
        nominal = (match.group(1) or match.group(2) or match.group(3) or "").strip()
        if nominal and not re.match(r"^0[.,]?0*$", nominal.replace(" ", "")):
            hasil.append(f"Rp. {nominal}")

    # Ambil semua nominal USD (skip yang 0)
    for match in re.finditer(r"USD\s*([\d,.]+)|\$\s*([\d,.]+)", raw_text, re.IGNORECASE):
        nominal = (match.group(1) or match.group(2)).strip()
        if not re.match(r"^0[.,]?0*$", nominal.replace(" ", "")):
            hasil.append(f"USD {nominal}")

    # Hilangkan duplikat
    hasil = list(dict.fromkeys(hasil))

    return " | ".join(hasil) if hasil else None

# ============================================================
# 4. CARI LINK HALAMAN FEE
# ============================================================
def find_fee_url(soup, base_url):
    text_keywords = ["publication fee", "author fee", "biaya publikasi", "publication cost", "author charge"]
    url_keywords  = ["fee", "biaya", "apc", "pubfee", "publication-fee", "authorfee", "author-fee"]
    skip_patterns = ["article/view", "issue/view", "announcement", "search", "login", "register"]

    links = soup.find_all("a", href=True)
    for link in links:
        teks = link.get_text(strip=True).lower()
        href = link['href'].lower()

        if any(skip in href for skip in skip_patterns):
            continue

        if any(kw in teks for kw in text_keywords) or any(kw in href for kw in url_keywords):
            href_original = link['href']
            return href_original if href_original.startswith("http") else urljoin(base_url, href_original)

    return None


# ============================================================
# 5. FUNGSI UTAMA
# ============================================================
def scrape_journal(url):
    print(f"\nScraping: {url}")

    soup, raw_text = get_page(url)
    if not raw_text:
        return None

    result = extract_info(raw_text)
    result["apc"] = None

    # Cari halaman fee dulu
    fee_url = find_fee_url(soup, url)
    if fee_url:
        print(f"  Halaman fee: {fee_url}")
        _, fee_raw = get_page(fee_url)
        if fee_raw:
            result["apc"] = extract_apc(fee_raw)

    # Kalau tidak ada halaman fee, baru cek free of charge di halaman utama
    if result["apc"] is None:
        if re.search(r"free of charge|no (?:publication |author )?fee|no charge|tanpa biaya", raw_text, re.IGNORECASE):
            result["apc"] = "Free"
        else:
            result["apc"] = "Tidak ditemukan"

    return result


# ============================================================
# 6. TEST
# ============================================================
urls = [
    "https://journal.irpi.or.id/index.php/malcom",
    "https://ejournal.kresnamediapublisher.com/index.php/jri",
    "https://journal.maranatha.edu/index.php/jutisi",
    "https://journal.uir.ac.id/index.php/JGEET",
    "https://ejurnal.seminar-id.com/index.php/bits/index",
    "https://ejurnal.seminar-id.com/index.php/tin",
    "https://hostjournals.com/bulletincsr",
    "https://journal.fkpt.org/index.php/BIT"

]

for url in urls:
    data = scrape_journal(url)
    if data:
        print("  " + "-" * 45)
        for key, value in data.items():
            print(f"  {key:12}: {value}")