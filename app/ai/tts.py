from pathlib import Path

from app.ai.openai_client import OpenAIClient
from app.config import get_settings


def generate_voiceover(text: str, output_path: Path, voice: str = "alloy") -> Path:
    settings = get_settings()
    if not settings.enable_tts:
        raise RuntimeError("ENABLE_TTS is false")
    client = OpenAIClient()
    audio_bytes = client.tts(settings.tts_model, voice, text)
    output_path.write_bytes(audio_bytes)
    return output_path
