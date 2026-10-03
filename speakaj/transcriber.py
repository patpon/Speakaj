"""Speech-to-text via Whisper-compatible HTTP APIs (Groq or OpenAI)."""

from __future__ import annotations

import requests

PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/audio/transcriptions",
        "model": "whisper-large-v3",
    },
    "openai": {
        "url": "https://api.openai.com/v1/audio/transcriptions",
        "model": "gpt-4o-transcribe",
    },
}

# A short bilingual prompt nudges Whisper to keep Thai in Thai script and
# English words in Latin script instead of transliterating either one.
BASE_PROMPT = "สวัสดีครับ วันนี้เราจะคุยเรื่อง project ใหม่ใน Google Sheets และ ChatGPT กันนะ"


class TranscriptionError(RuntimeError):
    pass


def build_prompt(dictionary: list[str]) -> str:
    if not dictionary:
        return BASE_PROMPT
    return f"{BASE_PROMPT} {', '.join(dictionary)}"


def transcribe(
    wav_bytes: bytes,
    *,
    provider: str,
    api_key: str,
    model: str = "",
    language: str = "",
    dictionary: list[str] | None = None,
    filename: str = "speech.wav",
    timeout: float = 60.0,
) -> str:
    if provider not in PROVIDERS:
        raise TranscriptionError(f"Unknown STT provider: {provider!r}")
    if not api_key:
        raise TranscriptionError(
            f"Missing API key for {provider}. Set {provider.upper()}_API_KEY "
            "in your environment or ~/.speakaj/.env"
        )

    spec = PROVIDERS[provider]
    data = {
        "model": model or spec["model"],
        "response_format": "json",
        "temperature": "0",
        "prompt": build_prompt(dictionary or []),
    }
    if language:
        data["language"] = language

    try:
        resp = requests.post(
            spec["url"],
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (filename, wav_bytes)},
            data=data,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise TranscriptionError(f"Network error: {exc}") from exc

    if resp.status_code != 200:
        raise TranscriptionError(f"{provider} STT failed ({resp.status_code}): {resp.text[:300]}")
    text = resp.json().get("text", "")
    return strip_prompt_echo(text.strip())


def strip_prompt_echo(text: str) -> str:
    """Whisper sometimes hallucinates the prompt on silent audio; drop it."""
    if text and text in BASE_PROMPT:
        return ""
    return text
