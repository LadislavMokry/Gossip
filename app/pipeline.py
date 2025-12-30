import json
from datetime import datetime, timezone

from app.ai.extract import extract_summary
from app.ai.first_judge import default_format_rules, judge_summary
from app.ai.generate import generate_for_model, generation_models
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


def mark_processed(article_id: str, summary: str, title: str | None = None) -> None:
    sb = get_supabase()
    update = {"summary": summary, "processed": True, "scraped_at": _now()}
    if title:
        update["title"] = title
    sb.table("articles").update(update).eq("id", article_id).execute()


def run_extraction(limit: int = 20) -> int:
    items = fetch_unprocessed(limit=limit)
    count = 0
    for item in items:
        raw = item.get("raw_html") or ""
        if not raw.strip():
            continue
        result = extract_summary(raw)
        summary = result.get("summary") or ""
        title = result.get("title")
        if summary:
            mark_processed(item["id"], summary, title)
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
    items = fetch_unscored(limit=limit)
    count = 0
    for item in items:
        summary = item.get("summary") or ""
        if not summary:
            continue
        result = judge_summary(summary)
        score = int(result.get("score", 0))
        formats = result.get("formats") or default_format_rules(score)
        mark_scored(item["id"], score, formats)
        count += 1
    return count


def _format_platform_map() -> dict:
    return {
        "headline": "instagram",
        "carousel": "instagram",
        "video": "tiktok",
        "podcast": "youtube",
    }


def fetch_ready_for_generation(limit: int = 10) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table("articles")
        .select("id, summary, format_assignments")
        .eq("scored", True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def has_posts(article_id: str) -> bool:
    sb = get_supabase()
    resp = sb.table("posts").select("id").eq("article_id", article_id).limit(1).execute()
    return bool(resp.data)


def insert_posts(article_id: str, model: str, content: dict, formats: list[str]) -> int:
    sb = get_supabase()
    platform_map = _format_platform_map()
    rows = []
    for fmt in formats:
        if fmt not in content:
            continue
        rows.append(
            {
                "article_id": article_id,
                "platform": platform_map.get(fmt, "instagram"),
                "content_type": fmt,
                "generating_model": model,
                "content": content.get(fmt),
            }
        )
    if not rows:
        return 0
    resp = sb.table("posts").insert(rows).execute()
    return len(resp.data or [])


def run_generation(limit: int = 10) -> int:
    items = fetch_ready_for_generation(limit=limit)
    count = 0
    for item in items:
        if has_posts(item["id"]):
            continue
        summary = item.get("summary") or ""
        formats = item.get("format_assignments") or []
        # Supabase returns JSONB as list or string; normalize
        if isinstance(formats, str):
            try:
                formats = json.loads(formats)
            except json.JSONDecodeError:
                formats = []
        if not formats:
            continue
        for model in generation_models():
            content = generate_for_model(summary, formats, model)
            count += insert_posts(item["id"], model, content, formats)
    return count


def fetch_for_second_judge(limit: int = 20) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table("posts")
        .select("id, article_id, content_type, generating_model, content, selected")
        .eq("selected", False)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def group_versions(items: list[dict]) -> dict:
    grouped: dict = {}
    for item in items:
        key = (item["article_id"], item["content_type"])
        grouped.setdefault(key, []).append(
            {
                "id": item["id"],
                "model": item["generating_model"],
                "content": item["content"],
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
        winner_model = decision.get("winner")
        # pick matching post id
        winner_post = next((v for v in versions if v["model"] == winner_model), None)
        if not winner_post:
            winner_post = versions[0]
        mark_post_selected(winner_post["id"])
        for v in versions:
            update_model_performance(v["model"], fmt, v["id"] == winner_post["id"])
        count += 1
    return count
