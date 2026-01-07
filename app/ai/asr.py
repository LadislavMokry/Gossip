from app.ai.openai_client import OpenAIClient
from app.config import get_settings


def transcribe_audio(audio_path: str, with_timestamps: bool = False):
    settings = get_settings()
    if not settings.enable_asr:
        raise RuntimeError("ENABLE_ASR is false")
    client = OpenAIClient()
    if with_timestamps:
        return client.asr(
            settings.asr_model,
            audio_path,
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )
    return client.asr(settings.asr_model, audio_path, response_format="text")
