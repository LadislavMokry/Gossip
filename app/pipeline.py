from datetime import datetime, timezone, timedelta

from app.ai.audio_roundup import generate_audio_roundup
from app.ai.extract import extract_summary
from app.ai.first_judge import default_format_rules, judge_summary
from app.ai.generate import generate_video_variant, generation_models
from app.ai.second_judge import pick_winner
from app.config import get_settings
from app.db import get_supabase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_unprocessed(limit: int = 20) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table("articles")
        .select("id, raw_html, title, source_url")
        .eq("processed", False)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def mark_processed(
    article_id: str, summary: str, title: str | None = None, content: str | None = None
) -> None:
    sb = get_supabase()
    update = {"summary": summary, "processed": True, "scraped_at": _now()}
    if title:
        update["title"] = title
    if content:
        update["content"] = content
    sb.table("articles").update(update).eq("id", article_id).execute()


def run_extraction(limit: int = 3) -> int:
    items = fetch_unprocessed(limit=limit)
    count = 0
    for item in items:
        raw = item.get("raw_html") or ""
        if not raw.strip():
            continue
        result = extract_summary(raw)
        summary = result.get("summary") or ""
        title = result.get("title")
        content = result.get("content")
        if summary:
            mark_processed(item["id"], summary, title, content)
            count += 1
    return count


def fetch_unscored(limit: int = 20) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table("articles")
        .select("id, summary")
        .eq("processed", True)
        .eq("scored", False)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def mark_scored(article_id: str, score: int, formats: list[str]) -> None:
    sb = get_supabase()
    sb.table("articles").update(
        {
            "judge_score": score,
            "format_assignments": formats,
            "scored": True,
        }
    ).eq("id", article_id).execute()


def run_first_judge(limit: int = 20) -> int:
    settings = get_settings()
    items = fetch_unscored(limit=limit)
    count = 0
    for item in items:
        summary = item.get("summary") or ""
        if not summary:
            continue
        result = judge_summary(summary)
        score = int(result.get("score", 0))
        formats = ["video"] if score >= settings.video_min_score else []
        mark_scored(item["id"], score, formats)
        count += 1
    return count


def fetch_ready_for_generation(limit: int = 10) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table("articles")
        .select("id, content, judge_score")
        .eq("scored", True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def has_video_posts(article_id: str) -> bool:
    sb = get_supabase()
    resp = (
        sb.table("posts")
        .select("id")
        .eq("article_id", article_id)
        .eq("content_type", "video")
        .limit(1)
        .execute()
    )
    return bool(resp.data)


def insert_video_post(article_id: str, model: str, content: dict) -> int:
    sb = get_supabase()
    row = {
        "article_id": article_id,
        "platform": "tiktok",
        "content_type": "video",
        "generating_model": model,
        "content": content,
    }
    resp = sb.table("posts").insert(row).execute()
    return len(resp.data or [])


def run_generation(limit: int = 10) -> int:
    settings = get_settings()
    models = generation_models()
    if not models:
        return 0
    model = models[0]
    items = fetch_ready_for_generation(limit=limit)
    count = 0
    for item in items:
        if has_video_posts(item["id"]):
            continue
        score = int(item.get("judge_score") or 0)
        if score < settings.video_min_score:
            continue
        content = (item.get("content") or "").strip()
        if not content:
            continue
        for variant_id in range(1, settings.generation_variants + 1):
            variant = generate_video_variant(content, model, variant_id)
            count += insert_video_post(item["id"], model, variant)
    return count


def fetch_for_second_judge(limit: int = 20) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table("posts")
        .select("id, article_id, content_type, generating_model, content, selected")
        .eq("selected", False)
        .eq("content_type", "video")
        .limit(limit)
        .execute()
    )
    return resp.data or []


def group_versions(items: list[dict]) -> dict:
    grouped: dict = {}
    for item in items:
        key = (item["article_id"], item["content_type"])
        content = item.get("content") or {}
        if isinstance(content, str):
            try:
                import json

                content = json.loads(content)
            except json.JSONDecodeError:
                content = {}
        variant_id = None
        if isinstance(content, dict):
            variant_id = content.get("variant_id")
        grouped.setdefault(key, []).append(
            {
                "id": item["id"],
                "model": item["generating_model"],
                "variant_id": variant_id,
                "content": content,
            }
        )
    return grouped


def mark_post_selected(post_id: str) -> None:
    sb = get_supabase()
    sb.table("posts").update({"selected": True}).eq("id", post_id).execute()


def update_model_performance(model: str, content_type: str, winner: bool) -> None:
    sb = get_supabase()
    try:
        sb.rpc(
            "update_model_performance",
            {"p_model_name": model, "p_content_type": content_type, "p_is_winner": winner},
        ).execute()
    except Exception:
        # If RPC not available, skip silently for MVP
        return


def run_second_judge(limit: int = 20) -> int:
    items = fetch_for_second_judge(limit=limit)
    grouped = group_versions(items)
    count = 0
    for (article_id, fmt), versions in grouped.items():
        decision = pick_winner(fmt, versions)
        winner_variant = decision.get("winner_variant") or decision.get("winner")
        # pick matching post id by variant
        winner_post = next(
            (v for v in versions if v.get("variant_id") == winner_variant), None
        )
        if not winner_post:
            winner_post = versions[0]
        mark_post_selected(winner_post["id"])
        for v in versions:
            update_model_performance(v["model"], fmt, v["id"] == winner_post["id"])
        count += 1
    return count


def fetch_for_audio_roundup(limit: int = 5, hours: int = 24) -> list[dict]:
    sb = get_supabase()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    resp = (
        sb.table("articles")
        .select("id, title, summary, judge_score, scraped_at")
        .eq("processed", True)
        .eq("scored", True)
        .gte("scraped_at", since.isoformat())
        .order("judge_score", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def insert_audio_roundup(model: str, content: dict) -> int:
    sb = get_supabase()
    row = {
        "article_id": None,
        "platform": "youtube",
        "content_type": "audio_roundup",
        "generating_model": model,
        "content": content,
    }
    resp = sb.table("posts").insert(row).execute()
    return len(resp.data or [])


def _project_language(project_id: str) -> str | None:
    sb = get_supabase()
    resp = (
        sb.table("projects")
        .select("language")
        .eq("id", project_id)
        .limit(1)
        .execute()
    )
    data = resp.data or []
    return data[0].get("language") if data else None


def run_audio_roundup(project_id: str | None = None, language: str | None = None) -> int:
    settings = get_settings()
    if project_id and not language:
        language = _project_language(project_id)
    items = fetch_for_audio_roundup(
        limit=settings.audio_roundup_size, hours=settings.audio_roundup_hours
    )
    if not items:
        return 0
    stories = [
        {"title": item.get("title"), "summary": item.get("summary")}
        for item in items
    ]
    content = generate_audio_roundup(stories, language=language)
    return insert_audio_roundup(settings.audio_roundup_model, content)


def fetch_latest_audio_roundup() -> dict | None:
    sb = get_supabase()
    resp = (
        sb.table("posts")
        .select("id, content")
        .eq("content_type", "audio_roundup")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    data = resp.data or []
    return data[0] if data else None


def fetch_latest_selected_video() -> dict | None:
    sb = get_supabase()
    resp = (
        sb.table("posts")
        .select("id, content")
        .eq("content_type", "video")
        .eq("selected", True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    data = resp.data or []
    return data[0] if data else None


def update_post_media(post_id: str, media_url: str) -> None:
    sb = get_supabase()
    sb.table("posts").update({"media_urls": [media_url]}).eq("id", post_id).execute()
