from app.ai.openai_client import OpenAIClient
from app.config import get_settings

LANGUAGE_LABELS = {
    "en": "English",
    "es": "Spanish",
    "sk": "Slovak",
}


def _language_label(value: str | None) -> str:
    if not value:
        return LANGUAGE_LABELS["en"]
    key = value.strip().lower()
    return LANGUAGE_LABELS.get(key, value.strip())


def _system_prompt(language: str | None) -> str:
    language_label = _language_label(language)
    return (
        f"You are a podcast writer. Write the script in {language_label}. "
        "Create a 3-5 minute audio roundup script for two hosts "
        "(host_a male, host_b female). Return JSON with keys: dialogue "
        "(array of {speaker, text}) and duration_seconds. Keep it concise, "
        "current, and engaging."
    )


def generate_audio_roundup(items: list[dict], language: str | None = None) -> dict:
    settings = get_settings()
    client = OpenAIClient()
    user = {
        "stories": items,
        "length_minutes": "3-5",
        "hosts": ["host_a", "host_b"],
    }
    return client.chat_json(
        model=settings.audio_roundup_model,
        system=_system_prompt(language),
        user=f"{user}\nReturn JSON.",
        temperature=0.6,
        max_tokens=1400,
        reasoning_effort="minimal",
    )
