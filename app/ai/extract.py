from app.config import get_settings
from app.ai.openai_client import OpenAIClient


SYSTEM_PROMPT = (
    "You are an extraction assistant. Extract and summarize the main content. "
    "Return JSON with keys: title, summary."
)


def extract_summary(raw_text: str) -> dict:
    settings = get_settings()
    client = OpenAIClient()
    user = f"Content:\n{raw_text}\n\nReturn JSON."
    return client.chat_json(
        model=settings.extraction_model,
        system=SYSTEM_PROMPT,
        user=user,
        temperature=0.1,
        max_tokens=600,
    )
