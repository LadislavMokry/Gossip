from app.ai.openai_client import OpenAIClient
from app.config import get_settings


def generate_image(prompt: str, size: str = "1024x1024", quality: str = "low") -> str:
    settings = get_settings()
    if not settings.enable_image_generation:
        raise RuntimeError("ENABLE_IMAGE_GENERATION is false")
    client = OpenAIClient()
    return client.image(settings.image_model, prompt, size=size, quality=quality)
