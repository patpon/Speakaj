"""Speech-to-text via Whisper-compatible HTTP APIs (Groq or OpenAI)."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/audio/transcriptions",
        "model": "whisper-large-v3",
        # Tried in order if the main model is rejected (e.g. decommissioned).
        "fallback_models": ["whisper-large-v3-turbo"],
    },
    "openai": {
        "url": "https://api.openai.com/v1/audio/transcriptions",
        "model": "gpt-4o-transcribe",
        "fallback_models": ["whisper-1"],
    },
    # Demo relay: a Groq proxy that checks a demo code instead of a key.
    "relay": {
        "url": "{relay_url}/v1/transcribe",
        "model": "whisper-large-v3",
        "fallback_models": ["whisper-large-v3-turbo"],
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
    relay_url: str = "",
) -> str:
    if provider not in PROVIDERS:
        raise TranscriptionError(f"Unknown STT provider: {provider!r}")
    if not api_key:
        if provider == "relay":
            raise TranscriptionError("ยังไม่ได้ใส่รหัสทดลอง (เปิดเมนู ตั้งค่า)")
        raise TranscriptionError(
            f"Missing API key for {provider}. Set {provider.upper()}_API_KEY "
            "in your environment or ~/.speakaj/.env"
        )

    spec = PROVIDERS[provider]
    url = spec["url"]
    headers = {"Authorization": f"Bearer {api_key}"}
    if provider == "relay":
        if not relay_url:
            raise TranscriptionError("ยังไม่ได้ตั้งค่า relay_url ของรหัสทดลอง")
        url = url.format(relay_url=relay_url.rstrip("/"))
        headers = {"X-Speakaj-Code": api_key}
    prompt = build_prompt(dictionary or [])
    models = [model or spec["model"]] + [m for m in spec["fallback_models"] if m != model]

    # On a 400 (bad request) retry without the prompt, then with fallback
    # models, so a too-long prompt or a retired model doesn't break dictation.
    attempts = [(models[0], prompt), (models[0], "")] + [(m, "") for m in models[1:]]
    last_error = ""
    for attempt_model, attempt_prompt in attempts:
        data = {"model": attempt_model, "response_format": "json", "temperature": "0"}
        if attempt_prompt:
            data["prompt"] = attempt_prompt
        if language:
            data["language"] = language
        try:
            resp = requests.post(
                url,
                headers=headers,
                files={"file": (filename, wav_bytes, "audio/wav")},
                data=data,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise TranscriptionError(f"Network error: {exc}") from exc

        if resp.status_code == 200:
            return strip_prompt_echo(resp.json().get("text", "").strip())
        last_error = f"{provider} STT failed ({resp.status_code}): {_error_message(resp)}"
        if provider == "relay" and resp.status_code in (401, 403, 429):
            # Demo-code problems (wrong, expired, daily limit) are already
            # written for the user by the relay.
            last_error = _error_message(resp)
        log.warning(
            "%s (model=%s, prompt=%s, audio=%d bytes)",
            last_error, attempt_model, bool(attempt_prompt), len(wav_bytes),
        )
        if resp.status_code != 400:
            break
    raise TranscriptionError(last_error)


def _error_message(resp) -> str:
    try:
        return str(resp.json()["error"]["message"])[:300]
    except (ValueError, KeyError, TypeError):
        return resp.text[:300]


def strip_prompt_echo(text: str) -> str:
    """Whisper sometimes hallucinates the prompt on silent audio; drop it."""
    if text and text in BASE_PROMPT:
        return ""
    return text
