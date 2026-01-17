from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests
import trafilatura

from .config import get_settings
from .db import get_supabase

MAX_CONTENT_CHARS = 4000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_iso(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    try:
        return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc).isoformat()
    except Exception:
        return None


def list_projects() -> list[dict]:
    sb = get_supabase()
    res = sb.table("projects").select("*").order("created_at", desc=True).execute()
    return res.data or []


def create_project(
    name: str,
    description: str | None = None,
    language: str | None = None,
    generation_interval_hours: int | None = None,
) -> dict:
    sb = get_supabase()
    row = {
        "name": name.strip(),
        "description": description,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    if language and language.strip():
        row["language"] = language.strip()
    if generation_interval_hours is not None:
        row["generation_interval_hours"] = generation_interval_hours
    res = sb.table("projects").insert(row).execute()
    return (res.data or [row])[0]


def update_project(project_id: str, fields: dict) -> dict:
    sb = get_supabase()
    payload = {k: v for k, v in fields.items() if v is not None}
    if "language" in payload and payload["language"]:
        payload["language"] = payload["language"].strip()
    payload["updated_at"] = _now_iso()
    res = sb.table("projects").update(payload).eq("id", project_id).execute()
    return (res.data or [payload])[0]


def delete_project(project_id: str) -> None:
    sb = get_supabase()
    sb.table("projects").delete().eq("id", project_id).execute()


def list_sources(project_id: str) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("sources")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


def get_source(source_id: str) -> dict | None:
    sb = get_supabase()
    res = sb.table("sources").select("*").eq("id", source_id).limit(1).execute()
    return (res.data or [None])[0]


def create_source(project_id: str, row: dict) -> dict:
    sb = get_supabase()
    payload = {
        "project_id": project_id,
        "name": row["name"].strip(),
        "source_type": row["source_type"].strip().lower(),
        "url": row["url"].strip(),
        "enabled": row.get("enabled", True),
        "config": row.get("config") or {},
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    if row.get("scrape_interval_hours") is not None:
        payload["scrape_interval_hours"] = row.get("scrape_interval_hours")
    res = sb.table("sources").insert(payload).execute()
    return (res.data or [payload])[0]


def update_source(source_id: str, fields: dict) -> dict:
    sb = get_supabase()
    payload = {k: v for k, v in fields.items() if v is not None}
    if "source_type" in payload and payload["source_type"]:
        payload["source_type"] = payload["source_type"].strip().lower()
    if "name" in payload and payload["name"]:
        payload["name"] = payload["name"].strip()
    if "url" in payload and payload["url"]:
        payload["url"] = payload["url"].strip()
    payload["updated_at"] = _now_iso()
    res = sb.table("sources").update(payload).eq("id", source_id).execute()
    return (res.data or [payload])[0]


def delete_source(source_id: str) -> None:
    sb = get_supabase()
    sb.table("sources").delete().eq("id", source_id).execute()


def list_source_items(source_id: str, limit: int = 10) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("source_items")
        .select("*")
        .eq("source_id", source_id)
        .order("scraped_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def get_youtube_account(project_id: str) -> dict | None:
    sb = get_supabase()
    res = (
        sb.table("youtube_accounts")
        .select("*")
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    return (res.data or [None])[0]


def upsert_youtube_account(project_id: str, refresh_token: str, channel_title: str | None, scopes: list[str] | None) -> dict:
    sb = get_supabase()
    payload = {
        "project_id": project_id,
        "refresh_token": refresh_token.strip(),
        "channel_title": channel_title,
        "scopes": scopes or [],
        "updated_at": _now_iso(),
        "created_at": _now_iso(),
    }
    res = sb.table("youtube_accounts").upsert(payload, on_conflict="project_id").execute()
    return (res.data or [payload])[0]


@dataclass
class ScrapeResult:
    source_id: str
    count: int
    status: str


def scrape_project(project_id: str, max_items: int = 10) -> list[ScrapeResult]:
    sources = [s for s in list_sources(project_id) if s.get("enabled", True)]
    results: list[ScrapeResult] = []
    for source in sources:
        results.append(scrape_source(source, max_items=max_items))
    return results


def scrape_source(source: dict, max_items: int = 10) -> ScrapeResult:
    source_id = source["id"]
    source_type = (source.get("source_type") or "").lower()
    url = source.get("url") or ""
    sb = get_supabase()
    status = "ok"
    count = 0
    try:
        if source_type in {"rss", "reddit", "youtube"}:
            count = _scrape_rss_source(sb, source_id, url, max_items=max_items)
        elif source_type in {"page", "website"}:
            count = _scrape_page_source(sb, source_id, url)
        else:
            status = f"unknown source_type: {source_type}"
    except Exception as exc:
        status = f"error: {exc.__class__.__name__}"
    sb.table("sources").update(
        {
            "last_scraped_at": _now_iso(),
            "last_status": status,
            "updated_at": _now_iso(),
        }
    ).eq("id", source_id).execute()
    return ScrapeResult(source_id=source_id, count=count, status=status)


def _scrape_rss_source(sb: Any, source_id: str, url: str, max_items: int) -> int:
    settings = get_settings()
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "application/rss+xml,application/xml,text/xml",
    }
    resp = requests.get(url, headers=headers, timeout=settings.request_timeout)
    resp.raise_for_status()
    feed = feedparser.parse(resp.text)
    rows: list[dict] = []
    for entry in feed.entries[:max_items]:
        link = entry.get("link") or entry.get("id")
        if not link:
            continue
        summary = entry.get("summary") or ""
        content = summary
        if not content and entry.get("content"):
            content = entry["content"][0].get("value", "")
        published = _to_iso(entry.get("published_parsed") or entry.get("updated_parsed"))
        rows.append(
            {
                "source_id": source_id,
                "title": entry.get("title"),
                "url": link,
                "content": (content or "")[:MAX_CONTENT_CHARS],
                "raw": (summary or "")[:MAX_CONTENT_CHARS],
                "published_at": published,
                "scraped_at": _now_iso(),
            }
        )
    if not rows:
        return 0
    return _upsert_items(sb, rows)


def _scrape_page_source(sb: Any, source_id: str, url: str) -> int:
    settings = get_settings()
    headers = {"User-Agent": settings.user_agent, "Accept": "text/html"}
    resp = requests.get(url, headers=headers, timeout=settings.request_timeout)
    resp.raise_for_status()
    extracted = trafilatura.extract(resp.text) or ""
    row = {
        "source_id": source_id,
        "title": url,
        "url": url,
        "content": extracted[:MAX_CONTENT_CHARS],
        "raw": extracted[:MAX_CONTENT_CHARS],
        "published_at": None,
        "scraped_at": _now_iso(),
    }
    return _upsert_items(sb, [row])


def _upsert_items(sb: Any, rows: list[dict]) -> int:
    if not rows:
        return 0
    # Caller injects source_id for each row.
    res = sb.table("source_items").upsert(rows, on_conflict="source_id,url").execute()
    return len(res.data or rows)
