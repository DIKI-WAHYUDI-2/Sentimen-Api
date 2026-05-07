import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
import trafilatura
from bs4 import BeautifulSoup
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE


INPUT_PATH = Path(r"C:\Users\LENOVO\Downloads\data-berita-ptpn iv reg iii-sept25-okt25.xlsx")
OUTPUT_PATH = Path(r"C:\Users\LENOVO\Downloads\data-berita-ptpn iv reg iii-sept25-okt25-dan isi..xlsx")

TITLE_ALIASES = {"judul", "title", "judul pemberitaan"}
LINK_ALIASES = {"link", "link pemberitaan", "url", "urls"}
ERROR_TEXT = "ERROR: tidak dapat mengambil konten"
REQUEST_TIMEOUT = 25
MAX_WORKERS = 12
SAVE_EVERY = 200


def normalize_name(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_excel_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    text = ILLEGAL_CHARACTERS_RE.sub("", text)
    text = text.replace("\x00", "")
    return text


def looks_like_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def load_candidate_rows(path: Path) -> pd.DataFrame:
    workbook = pd.ExcelFile(path)
    collected = []

    for sheet_name in workbook.sheet_names:
        df = workbook.parse(sheet_name)
        original_cols = {normalize_name(col): col for col in df.columns}
        title_col = next((original_cols[name] for name in TITLE_ALIASES if name in original_cols), None)
        link_col = next((original_cols[name] for name in LINK_ALIASES if name in original_cols), None)

        if not title_col or not link_col:
            continue

        part = df[[title_col, link_col]].copy()
        part.columns = ["judul", "link"]
        collected.append(part)

    if not collected:
        raise ValueError("Tidak ditemukan sheet dengan pasangan kolom judul dan link.")

    merged = pd.concat(collected, ignore_index=True)
    merged["judul"] = merged["judul"].map(normalize_text)
    merged["link"] = merged["link"].map(normalize_text)
    merged = merged[(merged["judul"] != "") | (merged["link"] != "")]
    merged["judul_key"] = merged["judul"].str.lower()
    merged["link_key"] = merged["link"].str.lower()
    merged = merged.drop_duplicates(subset=["judul_key", "link_key"], keep="first").reset_index(drop=True)
    return merged[["judul", "link"]]


def extract_with_bs4(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "iframe", "svg", "canvas", "form", "header", "footer", "nav", "aside"]):
        tag.decompose()

    for selector in [
        "article",
        "main",
        '[role="main"]',
        ".article-content",
        ".post-content",
        ".entry-content",
        ".content",
        ".news-content",
        ".td-post-content",
    ]:
        node = soup.select_one(selector)
        if not node:
            continue
        texts = [p.get_text(" ", strip=True) for p in node.find_all(["p", "h2", "h3", "li"])]
        cleaned = "\n".join(text for text in texts if len(text) >= 40)
        if len(cleaned) >= 200:
            return cleaned

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p) >= 40]
    if paragraphs:
        return "\n".join(paragraphs)

    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text


def fetch_article(session: requests.Session, url: str) -> str:
    if not url or not looks_like_url(url):
        return ERROR_TEXT

    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
        html = response.text
    except Exception:
        return ERROR_TEXT

    try:
        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            favor_precision=True,
        )
        if extracted:
            extracted = re.sub(r"\n{3,}", "\n\n", extracted).strip()
            if len(extracted) >= 120:
                return extracted
    except Exception:
        pass

    try:
        fallback = extract_with_bs4(html)
        fallback = re.sub(r"\n{3,}", "\n\n", fallback).strip()
        if len(fallback) >= 120:
            return fallback
    except Exception:
        pass

    return ERROR_TEXT


def save_output(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    export_df = df[["judul", "link", "isi_berita"]].copy()
    for column in export_df.columns:
        export_df[column] = export_df[column].map(clean_excel_text)
    export_df.to_excel(path, index=False)


def hydrate_from_existing(dataset: pd.DataFrame) -> pd.DataFrame:
    if not OUTPUT_PATH.exists():
        dataset["isi_berita"] = ""
        return dataset

    try:
        existing = pd.read_excel(OUTPUT_PATH)
    except Exception:
        dataset["isi_berita"] = ""
        return dataset

    if not {"judul", "link", "isi_berita"}.issubset(existing.columns):
        dataset["isi_berita"] = ""
        return dataset

    existing["judul"] = existing["judul"].map(normalize_text)
    existing["link"] = existing["link"].map(normalize_text)
    existing["isi_berita"] = existing["isi_berita"].map(normalize_text)
    existing = existing.drop_duplicates(subset=["judul", "link"], keep="first")

    dataset = dataset.merge(existing[["judul", "link", "isi_berita"]], on=["judul", "link"], how="left")
    dataset["isi_berita"] = dataset["isi_berita"].fillna("")
    return dataset


def main() -> int:
    dataset = load_candidate_rows(INPUT_PATH)
    dataset = hydrate_from_existing(dataset)

    total = len(dataset)
    pending_indexes = dataset.index[dataset["isi_berita"] == ""].tolist()
    print(f"Total baris unik: {total}")
    print(f"Perlu diproses: {len(pending_indexes)}")

    def worker(index: int):
        with requests.Session() as session:
            content = fetch_article(session, dataset.at[index, "link"])
        return index, content

    completed = total - len(pending_indexes)
    if pending_indexes:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(worker, index) for index in pending_indexes]
            for future in as_completed(futures):
                index, content = future.result()
                dataset.at[index, "isi_berita"] = content
                completed += 1
                if completed % 50 == 0 or completed == total:
                    error_count = int((dataset["isi_berita"] == ERROR_TEXT).sum())
                    print(f"Selesai {completed}/{total} | error sementara: {error_count}")
                if completed % SAVE_EVERY == 0:
                    save_output(dataset, OUTPUT_PATH)

    save_output(dataset, OUTPUT_PATH)
    error_count = int((dataset["isi_berita"] == ERROR_TEXT).sum())
    print(f"Output tersimpan: {OUTPUT_PATH}")
    print(f"Total error: {error_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
