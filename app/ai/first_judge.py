from app.ai.openai_client import OpenAIClient
from app.config import get_settings


SYSTEM_PROMPT = (
    "You are a content judge. Score the content 1-10 for viral potential. "
    "Return JSON with key: score (int)."
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
    if score >= 6:
        return ["video"]
    return []
