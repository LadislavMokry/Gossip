import os
from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    supabase_url: str
    supabase_key: str
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    manual_intake_script: str = "scripts/extract_text.py"
    manual_intake_dir: str | None = None
    max_words: int = 2500
    request_timeout: int = 30
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_KEY", "").strip()
    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_KEY. Set them in the environment."
        )
    return Settings(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        openai_base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        manual_intake_script=os.environ.get("MANUAL_INTAKE_SCRIPT", "scripts/extract_text.py"),
        manual_intake_dir=os.environ.get("MANUAL_INTAKE_DIR"),
        max_words=int(os.environ.get("MAX_WORDS", "2500")),
        request_timeout=int(os.environ.get("REQUEST_TIMEOUT", "30")),
        extraction_model=os.environ.get("EXTRACTION_MODEL", "gpt-5-nano"),
        judge_model=os.environ.get("JUDGE_MODEL", "gpt-4.1-mini"),
        second_judge_model=os.environ.get("SECOND_JUDGE_MODEL", "gpt-4.1-mini"),
        generation_models=[
            m.strip()
            for m in os.environ.get("GENERATION_MODELS", "gpt-4.1-mini").split(",")
            if m.strip()
        ],
        tts_model=os.environ.get("TTS_MODEL", "gpt-4o-mini-tts"),
        asr_model=os.environ.get("ASR_MODEL", "whisper-1"),
        image_model=os.environ.get("IMAGE_MODEL", "gpt-image-1"),
        enable_image_generation=os.environ.get("ENABLE_IMAGE_GENERATION", "false").lower()
        in ("1", "true", "yes"),
        enable_tts=os.environ.get("ENABLE_TTS", "false").lower() in ("1", "true", "yes"),
        enable_asr=os.environ.get("ENABLE_ASR", "false").lower() in ("1", "true", "yes"),
    )
    extraction_model: str = "gpt-5-nano"
    judge_model: str = "gpt-4.1-mini"
    second_judge_model: str = "gpt-4.1-mini"
    generation_models: list[str] = ["gpt-4.1-mini"]
    tts_model: str = "gpt-4o-mini-tts"
    asr_model: str = "whisper-1"
    image_model: str = "gpt-image-1"
    enable_image_generation: bool = False
    enable_tts: bool = False
    enable_asr: bool = False
