import json
from typing import Any

import requests

from app.config import get_settings


class OpenAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url.rstrip("/")
        self._timeout = settings.request_timeout

    def _supports_temperature(self, model: str) -> bool:
        return not model.startswith("gpt-5")

    def _default_reasoning_effort(self, model: str) -> str | None:
        if model.startswith("gpt-5"):
            return "minimal"
        return None

    def _supports_reasoning_effort(self, model: str) -> bool:
        return model.startswith("gpt-5")

    def _max_tokens_param(self, model: str) -> str:
        return "max_completion_tokens" if model.startswith("gpt-5") else "max_tokens"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def chat_json(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 800,
        reasoning_effort: str | None = None,
    ) -> dict:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            self._max_tokens_param(model): max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self._supports_temperature(model):
            payload["temperature"] = temperature
        effort = reasoning_effort or self._default_reasoning_effort(model)
        if effort and self._supports_reasoning_effort(model):
            payload["reasoning_effort"] = effort
        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self._timeout,
        )
        if not resp.ok:
            raise RuntimeError(f"OpenAI error {resp.status_code}: {resp.text}")
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not str(content).strip():
            raise RuntimeError(f"OpenAI returned empty content: {data}")
        return _parse_json(content)

    def chat_text(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.6,
        max_tokens: int = 800,
        reasoning_effort: str | None = None,
    ) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            self._max_tokens_param(model): max_tokens,
        }
        if self._supports_temperature(model):
            payload["temperature"] = temperature
        effort = reasoning_effort or self._default_reasoning_effort(model)
        if effort and self._supports_reasoning_effort(model):
            payload["reasoning_effort"] = effort
        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self._timeout,
        )
        if not resp.ok:
            raise RuntimeError(f"OpenAI error {resp.status_code}: {resp.text}")
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not str(content).strip():
            raise RuntimeError(f"OpenAI returned empty content: {data}")
        return content

    def tts(self, model: str, voice: str, text: str) -> bytes:
        payload = {"model": model, "voice": voice, "input": text}
        resp = requests.post(
            f"{self._base_url}/audio/speech",
            headers=self._headers(),
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.content

    def asr(self, model: str, audio_path: str) -> str:
        with open(audio_path, "rb") as f:
            resp = requests.post(
                f"{self._base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": f},
                data={"model": model},
                timeout=self._timeout,
            )
        resp.raise_for_status()
        return resp.json().get("text", "")

    def image(self, model: str, prompt: str, size: str = "1024x1024", quality: str = "low") -> str:
        payload = {"model": model, "prompt": prompt, "size": size, "quality": quality}
        resp = requests.post(
            f"{self._base_url}/images",
            headers=self._headers(),
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        # Expecting base64 or URL depending on API. Prefer URL if present.
        if "data" in data and data["data"]:
            return data["data"][0].get("url") or data["data"][0].get("b64_json", "")
        return ""


def _parse_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Fallback: try to extract JSON object from text
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise
