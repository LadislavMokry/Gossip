from app.ai.openai_client import OpenAIClient
from app.config import get_settings


def transcribe_audio(audio_path: str) -> str:
    settings = get_settings()
    if not settings.enable_asr:
        raise RuntimeError("ENABLE_ASR is false")
    client = OpenAIClient()
    return client.asr(settings.asr_model, audio_path)
