import re
from html import unescape

import trafilatura

from app.ai.openai_client import OpenAIClient
from app.config import get_settings

SYSTEM_PROMPT = (
    "You are an extraction assistant. Extract and summarize the main content. "
    "Return JSON with keys: title, summary, content."
)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\\s+", " ", text).strip()

def _extract_main_content(raw_html: str) -> str:
    if not raw_html:
        return ""
    extracted = trafilatura.extract(raw_html, include_comments=False, include_tables=False)
    if extracted:
        return extracted.strip()
    return _strip_html(raw_html)

def _fallback_summary(text: str, max_chars: int = 1000) -> str:
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:3]).strip()
    if not summary:
        summary = text[:max_chars].strip()
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0]
    return summary


def extract_summary(raw_text: str) -> dict:
    settings = get_settings()
    client = OpenAIClient()
    cleaned = _extract_main_content(raw_text)
    if len(cleaned) > settings.extraction_max_chars:
        cleaned = cleaned[: settings.extraction_max_chars]
    user = f"Content:\n{cleaned}\n\nReturn JSON."
    if not settings.extraction_use_llm:
        return {
            "title": None,
            "summary": _fallback_summary(cleaned),
            "content": cleaned,
        }
    try:
        result = client.chat_json(
            model=settings.extraction_model,
            system=SYSTEM_PROMPT,
            user=user,
            temperature=0.1,
            max_tokens=800,
            reasoning_effort="minimal",
        )
    except Exception as exc:
        return {
            "title": None,
            "summary": _fallback_summary(cleaned),
            "content": cleaned,
            "error": str(exc),
        }
    if isinstance(result, dict):
        result.setdefault("content", cleaned)
        if result.get("summary"):
            return result
    return {
        "title": None,
        "summary": _fallback_summary(cleaned),
        "content": cleaned,
    }
