from app.ai.openai_client import OpenAIClient
from app.config import get_settings

SYSTEM_PROMPT = (
    "You are a short-form video scriptwriter. Return JSON for a single video with keys: "
    "title, hook, script, scenes, captions, duration_seconds. "
    "scenes must be an array of 8-10 items. Each scene item must include: "
    "scene_text, image_prompt, duration_seconds. "
    "captions must be an array of short lines (<= 12 words each) aligned to the script. "
    "Language: Slovak. Keep it punchy and current."
)


def generate_video_variant(content: str, model: str, variant_id: int) -> dict:
    settings = get_settings()
    client = OpenAIClient()
    user = (
        "Article content:\n"
        f"{content}\n\n"
        f"Variant: {variant_id}\n"
        "Return JSON."
    )
    result = client.chat_json(
        model=model,
        system=SYSTEM_PROMPT,
        user=user,
        temperature=0.7,
        max_tokens=1400,
        reasoning_effort="minimal",
    )
    if isinstance(result, dict):
        result["variant_id"] = variant_id
    return result


def generation_models() -> list[str]:
    settings = get_settings()
    return settings.generation_models
