from app.ai.openai_client import OpenAIClient
from app.config import get_settings

SYSTEM_PROMPT = (
    "You are a Slovak podcast writer. Create a 3-5 minute audio roundup script "
    "for two hosts (host_a male, host_b female). Return JSON with keys: "
    "dialogue (array of {speaker, text}) and duration_seconds. Keep it concise, "
    "current, and engaging."
)


def generate_audio_roundup(items: list[dict]) -> dict:
    settings = get_settings()
    client = OpenAIClient()
    user = {
        "stories": items,
        "length_minutes": "3-5",
        "hosts": ["host_a", "host_b"],
    }
    return client.chat_json(
        model=settings.audio_roundup_model,
        system=SYSTEM_PROMPT,
        user=f"{user}\nReturn JSON.",
        temperature=0.6,
        max_tokens=1400,
        reasoning_effort="minimal",
    )
