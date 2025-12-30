from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlparse, urljoin
import re

import requests

from .config import get_settings
from .db import get_supabase


@dataclass(frozen=True)
class ScrapeSource:
    name: str
    url: str


DEFAULT_SOURCES = [
    ScrapeSource("topky.sk", "https://www.topky.sk/se/15/Prominenti"),
    ScrapeSource("cas.sk", "https://www.cas.sk/r/prominenti"),
    ScrapeSource("pluska.sk", "https://www1.pluska.sk/r/soubiznis"),
    ScrapeSource("refresher.sk", "https://refresher.sk/osobnosti"),
    ScrapeSource("startitup.sk", "https://www.startitup.sk/kategoria/kultura/"),
]


SITE_CONFIG = {
    "topky.sk": {
        "base": "https://www.topky.sk",
        "allow": [re.compile(r"https?://(?:www\.)?topky\.sk/cl/\d+/\d+/[^\"'\\s<>?#]+", re.I)],
        "extract": [re.compile(r"https?://(?:www\.)?topky\.sk/cl/\d+/\d+/[^\"'\\s<>?#]+", re.I)],
    },
    "cas.sk": {
        "base": "https://www.cas.sk",
        "href_only": True,
        "drop_trailing_dash": True,
        "allow": [re.compile(r"https?://(?:www\.)?cas\.sk/(?:premium/)?prominenti/[^\"'\\s<>?#]+", re.I)],
        "extract": [re.compile(r"https?://(?:www\.)?cas\.sk/(?:premium/)?prominenti/[^\"'\\s<>?#]+", re.I)],
    },
    "pluska.sk": {
        "base": "https://www1.pluska.sk",
        "allow": [
            re.compile(
                r"https?://(?:[a-z0-9-]+\\.)?pluska\\.sk/soubiznis/[^\"'\\s<>?#]+",
                re.I,
            )
        ],
        "extract": [
            re.compile(
                r"https?://(?:[a-z0-9-]+\\.)?pluska\\.sk/soubiznis/[^\"'\\s<>?#]+",
                re.I,
            )
        ],
        "deny": [
            re.compile(r"/cookie", re.I),
            re.compile(r"/predplatne", re.I),
            re.compile(r"/r/soubiznis", re.I),
        ],
    },
    "refresher.sk": {
        "base": "https://refresher.sk",
        "allow": [re.compile(r"https?://refresher\\.sk/\\d+[^\"'\\s<>?#]+", re.I)],
        "extract": [re.compile(r"https?://refresher\\.sk/\\d+[^\"'\\s<>?#]+", re.I)],
        "deny": [
            re.compile(r"\\.(?:js|css|jpg|jpeg|png|gif|webp|svg|woff2?)$", re.I),
        ],
    },
    "startitup.sk": {
        "base": "https://www.startitup.sk",
        "allow": [
            re.compile(
                r"https?://(?:www\\.)?startitup\\.sk/(?!kategoria|autor|tag|wp-|wp-content|videa|video|feed)[^\"'\\s<>?#]+",
                re.I,
            )
        ],
        "extract": [re.compile(r"https?://(?:www\\.)?startitup\\.sk/[^\"'\\s<>?#]+", re.I)],
        "deny": [
            re.compile(r"/wp-content", re.I),
            re.compile(r"/kategoria", re.I),
            re.compile(r"/videa", re.I),
            re.compile(r"/video", re.I),
            re.compile(r"/feed/", re.I),
            re.compile(r"#"),
        ],
    },
}


def _source_website(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or "unknown"


def _extract_hrefs(raw_html: str) -> list[str]:
    return re.findall(r'href=["\']([^"\']+)', raw_html, re.I)


def _normalize_url(url: str, base: str | None) -> str | None:
    if not url:
        return None
    url = unescape(url.strip())
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        if not base:
            return None
        url = urljoin(base, url)
    elif not url.startswith("http"):
        return None
    url = url.split("#")[0]
    url = url.split("?")[0]
    return url or None


def scrape_category_pages(sources: list[ScrapeSource] | None = None) -> list[dict]:
    settings = get_settings()
    rows = []
    for source in sources or DEFAULT_SOURCES:
        resp = requests.get(
            source.url,
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent, "Accept": "text/html"},
        )
        resp.raise_for_status()
        rows.append(
            {
                "source_url": source.url,
                "source_website": source.name or _source_website(source.url),
                "raw_html": resp.text,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return rows


def upsert_category_pages(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    supabase = get_supabase()
    response = supabase.table("category_pages").upsert(rows, on_conflict="source_url").execute()
    return response.data or []


def _should_keep(url: str, cfg: dict) -> bool:
    allow = cfg.get("allow") or []
    deny = cfg.get("deny") or []
    if allow and not any(r.search(url) for r in allow):
        return False
    if deny and any(r.search(url) for r in deny):
        return False
    if cfg.get("drop_trailing_dash"):
        if urlparse(url).path.endswith("-"):
            return False
    return True


def extract_article_urls(limit: int = 50) -> int:
    sb = get_supabase()
    pages = (
        sb.table("category_pages")
        .select("id, source_website, raw_html")
        .eq("processed", False)
        .limit(limit)
        .execute()
        .data
        or []
    )
    total = 0
    for page in pages:
        source = page.get("source_website")
        cfg = SITE_CONFIG.get(source)
        raw = page.get("raw_html") or ""
        if not cfg or not raw:
            sb.table("category_pages").update({"processed": True}).eq("id", page["id"]).execute()
            continue

        urls = set()
        base = cfg.get("base")
        for href in _extract_hrefs(raw):
            norm = _normalize_url(href, base)
            if not norm:
                continue
            if _should_keep(norm, cfg):
                urls.add(norm)
        if not cfg.get("href_only"):
            for regex in cfg.get("extract", []):
                for match in regex.findall(raw):
                    url = match if isinstance(match, str) else match[0]
                    norm = _normalize_url(url, base)
                    if not norm:
                        continue
                    if _should_keep(norm, cfg):
                        urls.add(norm)

        rows = [
            {
                "article_url": u,
                "source_website": source,
                "category_page_id": page["id"],
            }
            for u in urls
        ]
        if rows:
            sb.table("article_urls").upsert(rows, on_conflict="article_url").execute()
            total += len(rows)
        sb.table("category_pages").update({"processed": True}).eq("id", page["id"]).execute()
    return total


def scrape_article_pages(limit: int = 20) -> int:
    settings = get_settings()
    sb = get_supabase()
    urls = (
        sb.table("article_urls")
        .select("id, article_url, source_website")
        .eq("scraped", False)
        .limit(limit)
        .execute()
        .data
        or []
    )
    total = 0
    for row in urls:
        url = row["article_url"]
        try:
            resp = requests.get(
                url,
                timeout=settings.request_timeout,
                headers={"User-Agent": settings.user_agent, "Accept": "text/html"},
            )
        except requests.RequestException:
            # Leave scraped=false so it can be retried later
            print(f"[scrape-articles] request failed: {url}")
            continue

        if resp.status_code == 200:
            sb.table("articles").upsert(
                {
                    "source_url": url,
                    "source_website": row["source_website"],
                    "raw_html": resp.text,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="source_url",
            ).execute()
            sb.table("article_urls").update({"scraped": True}).eq("id", row["id"]).execute()
            total += 1
        else:
            print(f"[scrape-articles] non-200 {resp.status_code}: {url}")
        # Non-200 responses are left with scraped=false for retry
    return total
