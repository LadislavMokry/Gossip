from app.ai.openai_client import OpenAIClient
from app.config import get_settings


SYSTEM_PROMPT = (
    "You are a content judge. Score the content 1-10 and assign formats. "
    "Return JSON with keys: score (int), formats (array of strings). "
    "Formats allowed: headline, carousel, video, podcast."
)


def judge_summary(summary: str) -> dict:
    settings = get_settings()
    client = OpenAIClient()
    user = f"Summary:\n{summary}\n\nReturn JSON."
    return client.chat_json(
        model=settings.judge_model,
        system=SYSTEM_PROMPT,
        user=user,
        temperature=0.2,
        max_tokens=300,
    )


def default_format_rules(score: int) -> list[str]:
    if score >= 8:
        return ["headline", "carousel", "video", "podcast"]
    if score >= 6:
        return ["carousel", "headline"]
    if score >= 4:
        return ["headline"]
    return []
