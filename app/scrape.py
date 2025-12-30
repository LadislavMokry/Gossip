from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
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
        "allow": [re.compile(r"https?://(?:www\.)?topky\.sk/clanok/\d+/[^\"'\\s<>?#]+", re.I)],
        "extract": [re.compile(r"https?://(?:www\.)?topky\.sk/clanok/\d+/[^\"'\\s<>?#]+", re.I)],
    },
    "cas.sk": {
        "base": "https://www.cas.sk",
        "allow": [re.compile(r"https?://(?:www\.)?cas\.sk/(?:premium/)?prominenti/[^\"'\\s<>?#]+", re.I)],
        "extract": [re.compile(r"https?://(?:www\.)?cas\.sk/(?:premium/)?prominenti/[^\"'\\s<>?#]+", re.I)],
    },
    "pluska.sk": {
        "base": "https://www1.pluska.sk",
        "allow": [re.compile(r"https?://(?:www\\d*\\.)?pluska\\.sk/[^\"'\\s<>?#]+", re.I)],
        "extract": [re.compile(r"https?://(?:www\\d*\\.)?pluska\\.sk/[^\"'\\s<>?#]+", re.I)],
        "deny": [re.compile(r"/cookie", re.I), re.compile(r"/predplatne", re.I)],
    },
    "refresher.sk": {
        "base": "https://refresher.sk",
        "allow": [re.compile(r"https?://refresher\\.sk/\\d+[^\"'\\s<>?#]+", re.I)],
        "extract": [re.compile(r"https?://refresher\\.sk/\\d+[^\"'\\s<>?#]+", re.I)],
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
        for regex in cfg.get("extract", []):
            for match in regex.findall(raw):
                url = match if isinstance(match, str) else match[0]
                if _should_keep(url, cfg):
                    urls.add(url.split("#")[0])

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
        resp = requests.get(
            url,
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent, "Accept": "text/html"},
        )
        if resp.status_code == 200:
            sb.table("articles").insert(
                {
                    "source_url": url,
                    "source_website": row["source_website"],
                    "raw_html": resp.text,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()
            total += 1
        sb.table("article_urls").update({"scraped": True}).eq("id", row["id"]).execute()
    return total
