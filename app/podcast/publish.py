from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.db import get_supabase
from app.media.audio import render_audio_roundup
from app.media.paths import podcast_image_path, roundup_audio_path
from app.media.roundup_video import ensure_project_podcast_image
from app.podcast.meta import PodcastMeta, get_meta_for_project
from app.podcast.rss import PodcastEpisode, build_rss
from app.storage.r2 import upload_file, upload_text, public_url
from app.config import get_settings
import requests


@dataclass
class PublishResult:
    project_id: str
    project_name: str
    status: str
    rss_url: str | None = None
    audio_url: str | None = None
    image_url: str | None = None
    error: str | None = None


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9-_]+", "-", value).strip("-_")
    value = re.sub(r"-{2,}", "-", value)
    return value.lower() or "project"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def _project_row(project_id: str) -> dict | None:
    sb = get_supabase()
    resp = sb.table("projects").select("id,name").eq("id", project_id).limit(1).execute()
    data = resp.data or []
    return data[0] if data else None


def _project_meta(project_name: str) -> PodcastMeta | None:
    return get_meta_for_project(project_name)


def _project_roundups(project_id: str, limit: int = 30) -> list[dict]:
    sb = get_supabase()
    posts = (
        sb.table("posts")
        .select("id, content, created_at, podcast_url, podcast_posted, podcast_published_at")
        .eq("content_type", "audio_roundup")
        .order("created_at", desc=True)
        .limit(200)
        .execute()
        .data
        or []
    )
    if not posts:
        return []
    post_ids = [p.get("id") for p in posts if p.get("id")]
    usage = (
        sb.table("article_usage")
        .select("post_id, article_id")
        .in_("post_id", post_ids)
        .execute()
        .data
        or []
    )
    article_ids = list({u.get("article_id") for u in usage if u.get("article_id")})
    if not article_ids:
        return []
    articles = (
        sb.table("articles")
        .select("id, project_id")
        .in_("id", article_ids)
        .execute()
        .data
        or []
    )
    article_project = {a["id"]: a.get("project_id") for a in articles if a.get("id")}
    post_projects: dict[str, set[str]] = {}
    for row in usage:
        post_id = row.get("post_id")
        article_id = row.get("article_id")
        if post_id and article_id:
            proj = article_project.get(article_id)
            if proj:
                post_projects.setdefault(post_id, set()).add(proj)
    filtered = [p for p in posts if project_id in (post_projects.get(p.get("id")) or set())]
    return filtered[:limit]


def _ensure_audio_file(post_id: str, content: dict) -> Path:
    settings = get_settings()
    out_dir = Path(settings.media_output_dir)
    audio_path = roundup_audio_path(out_dir, post_id)
    if audio_path.exists():
        return audio_path
    dialogue = content.get("dialogue") or []
    voice_a = content.get("tts_voice_a")
    voice_b = content.get("tts_voice_b")
    render_audio_roundup(dialogue, audio_path, voice_a=voice_a, voice_b=voice_b)
    return audio_path


def _remote_length(url: str) -> int:
    try:
        resp = requests.head(url, timeout=10)
        if not resp.ok:
            return 0
        length = resp.headers.get("Content-Length")
        return int(length) if length else 0
    except Exception:
        return 0


def _ensure_artwork(project_id: str, prompt: str) -> Path:
    settings = get_settings()
    out_dir = Path(settings.media_output_dir)
    path = podcast_image_path(out_dir, project_id)
    if path.exists():
        return path
    image = ensure_project_podcast_image(prompt, path, allow_placeholder=False)
    if not image:
        raise RuntimeError("podcast image generation failed")
    return image


def _prepare_artwork(path: Path, size: int = 3000) -> Path:
    # Apple/Spotify artwork requirement: 3000x3000 square.
    from PIL import Image

    target = path.parent / "image_3000.png"
    img = Image.open(path)
    img = img.convert("RGB")
    if img.width == size and img.height == size:
        img.save(target)
        return target
    img = img.resize((size, size), Image.LANCZOS)
    img.save(target)
    return target


def _episode_title(content: dict) -> str:
    return content.get("title") or content.get("youtube_title") or "Daily Roundup"


def _episode_description(content: dict) -> str:
    return content.get("description") or "Daily roundup from OnePlace."


def _episode_duration(content: dict, audio_path: Path | None) -> int:
    # Prefer model-provided duration if present; fallback to file size timing if missing.
    try:
        seconds = int(content.get("duration_seconds") or 0)
        if seconds > 0:
            return seconds
    except Exception:
        pass
    # Last resort: estimate by file length (rough), but keep > 0.
    if not audio_path:
        return 0
    size = audio_path.stat().st_size
    return max(60, int(size / 16000))


def publish_podcast_for_project(project_id: str, refresh: bool = False) -> PublishResult:
    project = _project_row(project_id)
    if not project:
        return PublishResult(project_id=project_id, project_name="", status="missing_project")

    project_name = project.get("name") or project_id
    meta = _project_meta(project_name)
    if not meta:
        return PublishResult(
            project_id=project_id,
            project_name=project_name,
            status="missing_meta",
            error="No podcast metadata configured for project.",
        )

    posts = _project_roundups(project_id, limit=30)
    if not posts:
        return PublishResult(project_id=project_id, project_name=project_name, status="no_roundups")

    slug = _slugify(project_name)
    rss_key = f"podcasts/{slug}/rss.xml"
    artwork_key = f"podcasts/{slug}/artwork.png"

    settings = get_settings()
    image_url = None
    prompt = None
    sb = get_supabase()
    prompt_row = (
        sb.table("projects")
        .select("podcast_image_prompt")
        .eq("id", project_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if prompt_row:
        prompt = prompt_row[0].get("podcast_image_prompt")
    image_path = None
    if prompt and (settings.enable_image_generation or podcast_image_path(Path(settings.media_output_dir), project_id).exists()):
        try:
            image_path = _ensure_artwork(project_id, prompt)
        except Exception:
            image_path = None
    if image_path and image_path.exists():
        upload_path = _prepare_artwork(image_path)
        image_url = upload_file(
            upload_path,
            artwork_key,
            content_type="image/png",
            cache_control="public, max-age=31536000, immutable",
        )

    if not image_url:
        image_url = public_url(artwork_key)

    sb = get_supabase()
    episodes: list[PodcastEpisode] = []
    for post in posts:
        content = post.get("content") or {}
        if isinstance(content, str):
            try:
                import json

                content = json.loads(content)
            except Exception:
                content = {}
        post_id = post.get("id")
        if not post_id:
            continue
        audio_key = f"podcasts/{slug}/episodes/{post_id}.mp3"
        audio_url = post.get("podcast_url")
        audio_path = None
        if refresh or not audio_url:
            audio_path = _ensure_audio_file(post_id, content)
            audio_url = upload_file(
                audio_path,
                audio_key,
                content_type="audio/mpeg",
                cache_control="public, max-age=31536000, immutable",
            )
            sb.table("posts").update(
                {
                    "podcast_posted": True,
                    "podcast_url": audio_url,
                    "podcast_published_at": post.get("podcast_published_at") or _now_iso(),
                }
            ).eq("id", post_id).execute()
        if not audio_url:
            audio_url = public_url(audio_key)
        if audio_path is None and Path(get_settings().media_output_dir).exists():
            path = roundup_audio_path(Path(get_settings().media_output_dir), post_id)
            if path.exists():
                audio_path = path
        audio_length = audio_path.stat().st_size if audio_path and audio_path.exists() else _remote_length(audio_url)
        published_at = _parse_iso(post.get("podcast_published_at") or post.get("created_at"))
        episodes.append(
            PodcastEpisode(
                title=_episode_title(content),
                description=_episode_description(content),
                guid=post_id,
                audio_url=audio_url,
                audio_length=audio_length,
                duration_seconds=_episode_duration(content, audio_path),
                published_at=published_at,
            )
        )

    episodes_sorted = sorted(episodes, key=lambda e: e.published_at, reverse=True)
    rss_url = public_url(rss_key)
    rss_xml = build_rss(
        meta=meta,
        episodes=episodes_sorted,
        feed_url=rss_url,
        site_url=meta.site_url,
        image_url=image_url,
    )
    upload_text(rss_xml, rss_key, cache_control="public, max-age=300")

    return PublishResult(
        project_id=project_id,
        project_name=project_name,
        status="ok",
        rss_url=rss_url,
        audio_url=episodes_sorted[0].audio_url if episodes_sorted else None,
        image_url=image_url,
    )


def publish_podcasts_all(refresh: bool = False) -> list[PublishResult]:
    sb = get_supabase()
    projects = sb.table("projects").select("id,name").execute().data or []
    results: list[PublishResult] = []
    for project in projects:
        project_id = project.get("id")
        if not project_id:
            continue
        results.append(publish_podcast_for_project(project_id, refresh=refresh))
    return results
