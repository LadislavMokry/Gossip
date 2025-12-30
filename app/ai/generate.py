from app.ai.openai_client import OpenAIClient
from app.config import get_settings


SYSTEM_PROMPT = (
    "You are a social media content generator. Generate all requested formats in one response. "
    "Return JSON with keys for requested formats only. "
    "headline: string; carousel: array of strings; video: {script, duration_seconds}; "
    "podcast: {dialogue: array of strings}."
)


def generate_for_model(summary: str, formats: list[str], model: str) -> dict:
    settings = get_settings()
    client = OpenAIClient()
    format_list = ", ".join(formats) if formats else "none"
    user = f"Summary:\n{summary}\n\nFormats: {format_list}\nReturn JSON."
    return client.chat_json(
        model=model,
        system=SYSTEM_PROMPT,
        user=user,
        temperature=0.7,
        max_tokens=1200,
    )


def generation_models() -> list[str]:
    settings = get_settings()
    return settings.generation_models
