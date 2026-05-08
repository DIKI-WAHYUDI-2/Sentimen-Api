import logging
import os
import re
from datetime import datetime, timedelta, timezone
import json
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from requests.exceptions import HTTPError, SSLError

load_dotenv()

logger = logging.getLogger(__name__)

SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")
SERPAPI_URL = "https://serpapi.com/search"
SERPAPI_ENGINE = "google"
SEARCH_TOPICS = [
    "PTPN IV Regional III",
    "PalmCo",
    "Holding Perkebunan Nusantara",
    "PT Perkebunan Nusantara",
]

RELEVANT_TERMS = [
    "ptpn iv regional iii",
    "ptpn v",
]
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
CONTENT_SELECTORS = [
    "article",
    "[itemprop='articleBody']",
    ".article-content",
    ".post-content",
    ".entry-content",
    ".content",
    "main",
]
MAX_RANGE_DAYS = 31
SERPAPI_PAGE_SIZE = 10
MAX_SERPAPI_PAGES = 10
INDONESIAN_MONTHS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}
ARTICLE_DATE_META_SELECTORS = [
    ("meta", {"property": "article:published_time"}, "content"),
    ("meta", {"name": "article:published_time"}, "content"),
    ("meta", {"property": "og:published_time"}, "content"),
    ("meta", {"name": "pubdate"}, "content"),
    ("meta", {"name": "publishdate"}, "content"),
    ("meta", {"name": "publish-date"}, "content"),
    ("meta", {"name": "parsely-pub-date"}, "content"),
    ("meta", {"name": "date"}, "content"),
]


def normalize_date_input(raw_value):
    if raw_value is None:
        return None
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Date format must be YYYY-MM-DD") from exc


def get_today_date():
    return datetime.now(timezone.utc).date()


def validate_date_range(start_date, end_date):
    today = get_today_date()

    if start_date > today:
        raise ValueError("start_date cannot be in the future")

    if end_date > today:
        raise ValueError("end_date cannot be in the future")

    if start_date > end_date:
        raise ValueError("start_date cannot be later than end_date")

    range_length = (end_date - start_date).days + 1
    if range_length > MAX_RANGE_DAYS:
        raise ValueError(f"Date range cannot exceed {MAX_RANGE_DAYS} days")


def resolve_date_range(search_params):
    start_date_value = search_params.get("start_date")
    end_date_value = search_params.get("end_date")

    if not start_date_value and not end_date_value:
        return None, None

    if not start_date_value:
        raise ValueError("start_date is required")

    parsed_start = normalize_date_input(start_date_value)
    parsed_end = normalize_date_input(end_date_value) if end_date_value else parsed_start

    validate_date_range(parsed_start, parsed_end)
    return parsed_start, parsed_end


def resolve_search_queries(search_params):
    selected_keyword = (search_params.get("keyword") or "").strip()
    if not selected_keyword:
        return [SEARCH_TOPICS[0]]
    if selected_keyword not in SEARCH_TOPICS:
        raise ValueError("Keyword scraping tidak valid")
    return [selected_keyword]


def parse_serpapi_date(raw_value):
    """Parse absolute date strings returned by Google Search engine (via SerpAPI).

    Google Search engine always returns absolute dates, so we only handle
    absolute formats. The primary fields from the API are:
      - ``published_at``: e.g. "2026-02-18 08:00:00 UTC"
      - ``date``        : e.g. "18 Feb 2026"
    """
    if not raw_value:
        return None

    # Priority: published_at format first, then date field format, then fallbacks
    for fmt in (
        "%Y-%m-%d %H:%M:%S UTC",  # "2026-02-18 08:00:00 UTC"  <- published_at
        "%d %b %Y",               # "18 Feb 2026"              <- date
        "%m/%d/%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw_value.strip(), fmt).date()
        except ValueError:
            continue

    logger.warning("parse_serpapi_date: unrecognized date format", extra={"raw_value": raw_value})
    return None


def parse_article_date(raw_value):
    if not raw_value:
        return None

    cleaned = re.sub(r"\s+", " ", str(raw_value).strip())
    lowered = cleaned.lower()

    iso_candidate = cleaned.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_candidate).date()
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %B %Y",
        "%d %B %Y %H:%M",
        "%d %B %Y %H:%M WIB",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    indo_absolute_match = re.search(
        r"(?:(?:senin|selasa|rabu|kamis|jumat|sabtu|minggu)\s*,?\s*)?(\d{1,2})\s+"
        r"(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s+"
        r"(\d{4})",
        lowered,
    )
    if indo_absolute_match:
        try:
            day = int(indo_absolute_match.group(1))
            month = INDONESIAN_MONTHS[indo_absolute_match.group(2)]
            year = int(indo_absolute_match.group(3))
            return datetime(year, month, day).date()
        except ValueError:
            pass

    slash_match = re.search(r"(\d{4})/(\d{2})/(\d{2})", cleaned)
    if slash_match:
        try:
            year, month, day = map(int, slash_match.groups())
            return datetime(year, month, day).date()
        except ValueError:
            pass

    return None


def _extract_date_from_json_ld(soup):
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw_text = script.string or script.get_text(strip=True)
        if not raw_text:
            continue

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            continue

        candidates = payload if isinstance(payload, list) else [payload]
        while candidates:
            candidate = candidates.pop(0)
            if isinstance(candidate, list):
                candidates.extend(candidate)
                continue
            if not isinstance(candidate, dict):
                continue

            for key in ("datePublished", "dateCreated", "uploadDate", "dateModified"):
                parsed = parse_article_date(candidate.get(key))
                if parsed:
                    return parsed

            graph = candidate.get("@graph")
            if graph:
                candidates.append(graph)

    return None


def extract_article_date(soup, url=None):
    for tag_name, attrs, value_key in ARTICLE_DATE_META_SELECTORS:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get(value_key):
            parsed = parse_article_date(tag.get(value_key))
            if parsed:
                return parsed

    time_tag = soup.find("time")
    if time_tag:
        for value in (time_tag.get("datetime"), time_tag.get_text(" ", strip=True)):
            parsed = parse_article_date(value)
            if parsed:
                return parsed

    parsed_json_ld = _extract_date_from_json_ld(soup)
    if parsed_json_ld:
        return parsed_json_ld

    text_candidates = soup.find_all(
        string=re.compile(
            r"(\d{1,2}\s+(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s+\d{4})|(\d{4}/\d{2}/\d{2})",
            re.IGNORECASE,
        )
    )
    for candidate in text_candidates[:20]:
        parsed = parse_article_date(candidate)
        if parsed:
            return parsed

    if url:
        parsed = parse_article_date(url)
        if parsed:
            return parsed

    return None


def is_date_in_range(candidate_date, start_date, end_date):
    if start_date is None and end_date is None:
        return True
    if candidate_date is None:
        return False
    return start_date <= candidate_date <= end_date


def normalize_text(value):
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def is_relevant_news_item(title, source, content):
    haystack = " ".join(
        [
            normalize_text(title),
            normalize_text(source),
            normalize_text(content),
        ]
    )
    return any(term in haystack for term in RELEVANT_TERMS)


def _extract_text_from_container(container):
    if not container:
        return None
    paragraphs = [paragraph.get_text(" ", strip=True) for paragraph in container.find_all("p")]
    content = " ".join(text for text in paragraphs if len(text) > 40).strip()
    return content or None


def extract_metadata(url, session=None):
    if not url or not url.startswith("http"):
        return {"content": None, "published_at": None}

    request_session = session or requests.Session()
    fallback_published_at = parse_article_date(url)

    def _request_article(verify=True, extra_headers=None):
        headers = dict(REQUEST_HEADERS)
        if extra_headers:
            headers.update(extra_headers)
        return request_session.get(url, headers=headers, timeout=20, verify=verify)

    response = None
    try:
        response = _request_article()
        response.raise_for_status()
    except SSLError:
        logger.warning("SSL verification failed for article, retrying without certificate verification")
        try:
            requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]
            response = _request_article(verify=False)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            logger.warning("Failed to fetch article details after SSL retry", exc_info=True)
            return {
                "content": None,
                "published_at": fallback_published_at.isoformat() if fallback_published_at else None,
            }
    except HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 403:
            logger.warning("Article request returned 403, retrying with referer headers")
            hostname = urlparse(url).netloc
            retry_headers = {
                "Referer": f"https://{hostname}/",
                "Upgrade-Insecure-Requests": "1",
            }
            try:
                response = _request_article(extra_headers=retry_headers)
                response.raise_for_status()
            except requests.exceptions.RequestException:
                logger.warning("Failed to fetch article details after 403 retry", exc_info=True)
                return {
                    "content": None,
                    "published_at": fallback_published_at.isoformat() if fallback_published_at else None,
                }
        else:
            logger.warning("Failed to fetch article details", exc_info=True)
            return {
                "content": None,
                "published_at": fallback_published_at.isoformat() if fallback_published_at else None,
            }
    except requests.exceptions.RequestException:
        logger.warning("Failed to fetch article details", exc_info=True)
        return {
            "content": None,
            "published_at": fallback_published_at.isoformat() if fallback_published_at else None,
        }

    soup = BeautifulSoup(response.text, "html.parser")
    published_at = extract_article_date(soup, url=url)

    for tag_name in ("script", "style", "noscript", "iframe", "footer", "header"):
        for tag in soup.find_all(tag_name):
            tag.decompose()

    content = None
    for selector in CONTENT_SELECTORS:
        content = _extract_text_from_container(soup.select_one(selector))
        if content:
            break

    if not content:
        paragraphs = [paragraph.get_text(" ", strip=True) for paragraph in soup.find_all("p")]
        content = " ".join(text for text in paragraphs if len(text) > 40).strip() or None

    return {
        "content": content,
        "published_at": published_at.isoformat() if published_at else None,
    }


def build_search_params(query, start_date, end_date, start=0):
    params = {
        "engine": SERPAPI_ENGINE,
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "location": "Indonesia",
        "google_domain": "google.co.id",
        "hl": "id",
        "gl": "id",
        "tbm": "nws",
        "device": "desktop",
        "no_cache": "true",
        "start": start,
    }

    if start_date and end_date:
        cd_min = start_date.strftime("%m/%d/%Y")
        cd_max = end_date.strftime("%m/%d/%Y")
        params["tbs"] = f"cdr:1,cd_min:{cd_min},cd_max:{cd_max}"

    return params


def get_news(search_params):
    if not SERPAPI_API_KEY:
        raise ValueError("SERPAPI_API_KEY is not configured")

    start_date, end_date = resolve_date_range(search_params)
    search_queries = resolve_search_queries(search_params)
    request_session = requests.Session()
    seen_keys = set()
    results = []

    for query in search_queries:
        logger.info("Fetching news from SerpAPI", extra={"query": query})
        seen_query_page_keys = set()
        page_index = 0
        while True:
            start = page_index * SERPAPI_PAGE_SIZE
            try:
                response = request_session.get(
                    SERPAPI_URL,
                    params=build_search_params(query, start_date, end_date, start=start),
                    timeout=20,
                )
                response.raise_for_status()
            except requests.exceptions.RequestException:
                logger.warning(
                    "Failed to fetch SerpAPI results",
                    exc_info=True,
                    extra={"query": query, "start": start},
                )
                break

            items = response.json().get("news_results", [])
            if not items:
                logger.info("No more SerpAPI results for query", extra={"query": query, "start": start})
                break

            new_items_in_page = 0
            for item in items:
                url = item.get("link", "")
                title = item.get("title", "")
                page_key = url or normalize_text(title)
                if page_key in seen_query_page_keys:
                    continue
                seen_query_page_keys.add(page_key)
                new_items_in_page += 1

                metadata = extract_metadata(url, session=request_session)
                # Google Search engine returns source as a plain string
                raw_source = item.get("source", "Unknown source")
                source_name = str(raw_source) if raw_source else "Unknown source"
                content = metadata.get("content")
                article_published_date = parse_article_date(metadata.get("published_at"))
                # Prefer published_at from SerpAPI (absolute ISO-like format) over date field
                serpapi_raw_date = item.get("published_at") or item.get("date", "")
                serpapi_published_date = parse_serpapi_date(serpapi_raw_date)
                published_date = article_published_date or serpapi_published_date

                if not is_date_in_range(published_date, start_date, end_date):
                    continue

                if not is_relevant_news_item(title, source_name, content):
                    continue

                dedupe_key = url or normalize_text(title)
                if dedupe_key in seen_keys:
                    continue

                results.append(
                    {
                        "title": title,
                        "source": source_name,
                        "date": published_date.isoformat() if published_date else None,
                        "url": url,
                        "content": content,
                    }
                )
                seen_keys.add(dedupe_key)

            if len(items) < SERPAPI_PAGE_SIZE or new_items_in_page == 0:
                break

            page_index += 1

    logger.info("Scraper completed", extra={"status_code": len(results)})
    return results
