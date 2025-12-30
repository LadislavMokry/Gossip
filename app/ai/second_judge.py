from app.ai.openai_client import OpenAIClient
from app.config import get_settings


SYSTEM_PROMPT = (
    "You are a judge selecting the best version. Return JSON with keys: winner, reasoning."
)


def pick_winner(format_name: str, versions: list[dict]) -> dict:
    settings = get_settings()
    if not versions:
        return {"winner": None, "reasoning": "no versions"}
    if not settings.openai_api_key:
        return {"winner": versions[0]["model"], "reasoning": "default first (no API key)"}

    client = OpenAIClient()
    user = {
        "format": format_name,
        "versions": versions,
    }
    return client.chat_json(
        model=settings.second_judge_model,
        system=SYSTEM_PROMPT,
        user=f"{user}\nReturn JSON.",
        temperature=0.2,
        max_tokens=400,
    )
