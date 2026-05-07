from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20
MIN_PARAGRAPH_LENGTH = 40
CONTENT_SELECTORS = [
    "article",
    "main",
    "[itemprop='articleBody']",
    ".article-content",
    ".post-content",
    ".entry-content",
    ".td-post-content",
    ".read__content",
    ".detail__body-text",
    ".content__article-body",
    ".news-content",
    ".story-content",
    ".post-body",
    ".article__content",
    ".content-detail",
]


@dataclass
class ScrapeResult:
    link: str
    title: str = ""
    body: str = ""
    status: str = ""


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )
    return session


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def dedupe_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def get_title(soup: BeautifulSoup) -> str:
    for selector, attr in [
        ("meta[property='og:title']", "content"),
        ("meta[name='twitter:title']", "content"),
        ("meta[name='title']", "content"),
    ]:
        tag = soup.select_one(selector)
        if tag and tag.get(attr):
            return clean_text(tag.get(attr, ""))

    if soup.title and soup.title.string:
        title = clean_text(soup.title.string)
        if title:
            return title

    h1 = soup.find("h1")
    if h1:
        return clean_text(h1.get_text(" ", strip=True))

    return ""


def remove_noise(container: BeautifulSoup) -> None:
    for tag in container.select(
        "script, style, noscript, svg, form, button, nav, footer, header, "
        "aside, iframe, figure, figcaption, .share, .social, .related, "
        ".ads, .advertisement, .promo, .breadcrumb, .comment, .newsletter"
    ):
        tag.decompose()


def extract_paragraphs(container: BeautifulSoup) -> list[str]:
    paragraphs: list[str] = []
    for tag in container.find_all(["p", "li", "blockquote"]):
        text = clean_text(tag.get_text(" ", strip=True))
        if len(text) >= MIN_PARAGRAPH_LENGTH:
            paragraphs.append(text)

    if paragraphs:
        return dedupe_keep_order(paragraphs)

    fallback_chunks: list[str] = []
    for text in container.stripped_strings:
        normalized = clean_text(text)
        if len(normalized) >= MIN_PARAGRAPH_LENGTH:
            fallback_chunks.append(normalized)
    return dedupe_keep_order(fallback_chunks)


def candidate_score(tag) -> int:
    text = clean_text(tag.get_text(" ", strip=True))
    paragraph_count = len(tag.find_all("p"))
    return len(text) + paragraph_count * 200


def find_best_container(soup: BeautifulSoup):
    for selector in CONTENT_SELECTORS:
        node = soup.select_one(selector)
        if node:
            return node

    candidates = []
    for tag in soup.find_all(["div", "section"], limit=300):
        classes = " ".join(tag.get("class", []))
        identifier = f"{tag.get('id', '')} {classes}".lower()
        if any(
            token in identifier
            for token in ["content", "article", "post", "body", "entry", "detail", "story"]
        ):
            candidates.append(tag)

    if not candidates:
        candidates = soup.find_all(["article", "main", "div", "section"], limit=300)

    best = None
    best_score = 0
    for tag in candidates:
        score = candidate_score(tag)
        if score > best_score:
            best = tag
            best_score = score
    return best


def extract_article(html: str) -> tuple[str, str, str]:
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return "", "", "Gagal parsing HTML"

    title = get_title(soup)
    container = find_best_container(soup)
    if container is None:
        return title, "", "Konten tidak ditemukan"

    remove_noise(container)
    paragraphs = extract_paragraphs(container)
    if not paragraphs:
        return title, "", "Konten tidak ditemukan"

    body = "\n\n".join(paragraphs)
    if len(body) < 100:
        return title, "", "Konten tidak ditemukan"

    return title, body, "OK"


def fetch_page(session: requests.Session, link: str) -> Response:
    return session.get(link, timeout=REQUEST_TIMEOUT, allow_redirects=True)


def scrape_link(session: requests.Session, link: str) -> ScrapeResult:
    try:
        response = fetch_page(session, link)
    except requests.exceptions.Timeout:
        return ScrapeResult(link=link, status="Timeout")
    except requests.exceptions.SSLError as exc:
        return ScrapeResult(link=link, status=f"SSL Error: {clean_text(str(exc))[:120]}")
    except requests.exceptions.ConnectionError as exc:
        return ScrapeResult(link=link, status=f"Connection Error: {clean_text(str(exc))[:120]}")
    except requests.exceptions.RequestException as exc:
        return ScrapeResult(link=link, status=f"Request Error: {clean_text(str(exc))[:120]}")
    except Exception as exc:
        return ScrapeResult(link=link, status=f"Error: {clean_text(str(exc))[:120]}")

    if response.status_code >= 400:
        return ScrapeResult(link=link, status=f"{response.status_code} {response.reason}")

    title, body, status = extract_article(response.text)
    if status != "OK":
        return ScrapeResult(link=link, status=status)

    return ScrapeResult(link=link, title=title, body=body, status="OK")


def load_links(input_path: Path, sheet_name: str) -> list[str]:
    df = pd.read_excel(input_path, sheet_name=sheet_name)
    first_col = df.columns[0]
    links = []
    for value in df[first_col].tolist():
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text:
            links.append(text)
    return links


def save_results(results: list[ScrapeResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {
                "Link": row.link,
                "Judul": row.title,
                "Isi Berita": row.body,
                "Status / Keterangan": row.status,
            }
            for row in results
        ]
    )
    df.to_excel(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sheet", default="Data")
    parser.add_argument("--output", required=True)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    links = load_links(input_path, args.sheet)
    session = build_session()

    results: list[ScrapeResult] = []
    total = len(links)
    print(f"Memproses {total} link dari {input_path}")

    for index, link in enumerate(links, start=1):
        result = scrape_link(session, link)
        results.append(result)
        print(f"[{index}/{total}] {result.status} | {link}")
        if args.delay > 0 and index < total:
            time.sleep(args.delay)

    save_results(results, output_path)
    print(f"Hasil tersimpan di {output_path}")


if __name__ == "__main__":
    main()
