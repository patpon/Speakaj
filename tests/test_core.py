import io
import json
import wave
from types import SimpleNamespace

import numpy as np
import pytest

from speakaj import cleaner, stats, transcriber
from speakaj.config import Config, load_config
from speakaj.recorder import is_silent, to_wav_bytes


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("um so I think uh we should go", "So I think we should go"),
        ("เอ่อ วันนี้ อืม ไปกินข้าวกัน", "วันนี้ ไปกินข้าวกัน"),
        ("ผมอ่านหนังสือ", "ผมอ่านหนังสือ"),  # "อ่า" inside a real word stays
        ("the the meeting is at 3", "The meeting is at 3"),
        ("ส่งไฟล์ให้หน่อย. ขอบคุณครับ", "ส่งไฟล์ให้หน่อย ขอบคุณครับ"),
        ("hello , world", "Hello, world"),
        ("เอ่อ", ""),
    ],
)
def test_clean_local(raw, expected):
    assert cleaner.clean_local(raw) == expected


def test_clean_falls_back_to_local_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = Config(anthropic_api_key="")
    assert cleaner.clean("uh hello", cfg) == "Hello"


def test_clean_falls_back_when_claude_errors(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(cleaner, "clean_with_claude", boom)
    cfg = Config(anthropic_api_key="x")
    assert cleaner.clean("um ok", cfg) == "Ok"


def test_clean_with_claude_request(monkeypatch):
    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=" สวัสดี ")],
            )

    class FakeClient:
        def __init__(self, **kw):
            self.messages = FakeMessages()
            self.beta = SimpleNamespace(messages=FakeMessages())

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    out = cleaner.clean_with_claude("เอ่อ สวัสดี", api_key="k", model="claude-opus-5-5", dictionary=["Speakaj"])
    assert out == "สวัสดี"
    assert captured["fallbacks"] == "default"
    assert captured["output_config"] == {"effort": "low"}
    assert "<transcript>" in captured["messages"][0]["content"]
    assert "Speakaj" in captured["system"]


def test_count_words():
    assert stats.count_words("hello world") == 2
    assert stats.count_words("") == 0
    assert stats.count_words("สวัสดีครับ") == 2  # 10 Thai chars ~ 2 words
    assert stats.count_words("เปิด Google Sheets") == 3


def test_stats_rollover(tmp_path):
    path = tmp_path / "stats.json"
    path.write_text(json.dumps({"week": "2000-W01", "week_words": 999, "total_words": 999, "dictations": 1}))
    s = stats.Stats(path)
    assert s.week_words == 0
    s.add(5)
    assert s.week_words == 5
    assert json.loads(path.read_text())["total_words"] == 1004
    assert s.over_limit(5) and not s.over_limit(0)


def test_history(tmp_path):
    path = tmp_path / "h.jsonl"
    stats.append_history("uh hi", "Hi", 1.0, path)
    stats.append_history("เอ่อ ไป", "ไป", 1.0, path)
    assert stats.last_history(path) == "ไป"


def test_wav_roundtrip():
    samples = np.sin(np.linspace(0, 100, 16000)).astype("float32") * 0.5
    data = to_wav_bytes(samples, 16000)
    with wave.open(io.BytesIO(data)) as w:
        assert w.getnchannels() == 1
        assert w.getframerate() == 16000
        assert w.getnframes() == 16000
    assert not is_silent(samples)
    assert is_silent(np.zeros(100, "float32"))
    assert is_silent(np.zeros(0, "float32"))


def test_config_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    cfg = load_config(path)
    assert path.is_file()
    cfg.hotkey = "alt_r"
    cfg.save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["unknown_field"] = 1
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_config(path).hotkey == "alt_r"

    monkeypatch.setenv("GROQ_API_KEY", "from-env")
    assert Config(groq_api_key="file").api_key("groq") == "from-env"


def test_transcribe_requires_key():
    with pytest.raises(transcriber.TranscriptionError):
        transcriber.transcribe(b"", provider="groq", api_key="")


def test_transcribe_request(monkeypatch):
    sent = {}

    def fake_post(url, headers, files, data, timeout):
        sent.update(url=url, headers=headers, data=data)
        return SimpleNamespace(status_code=200, json=lambda: {"text": " สวัสดี hello "}, text="")

    monkeypatch.setattr(transcriber.requests, "post", fake_post)
    out = transcriber.transcribe(b"x", provider="groq", api_key="k", dictionary=["Speakaj"])
    assert out == "สวัสดี hello"
    assert sent["url"].startswith("https://api.groq.com")
    assert sent["data"]["model"] == "whisper-large-v3"
    assert "Speakaj" in sent["data"]["prompt"]
    assert "language" not in sent["data"]


def test_transcribe_retries_on_400(monkeypatch):
    calls = []

    def fake_post(url, headers, files, data, timeout):
        calls.append(dict(data))
        if len(calls) < 3:
            return SimpleNamespace(
                status_code=400, json=lambda: {"error": {"message": "bad"}}, text="bad"
            )
        return SimpleNamespace(status_code=200, json=lambda: {"text": "ok"}, text="")

    monkeypatch.setattr(transcriber.requests, "post", fake_post)
    assert transcriber.transcribe(b"x", provider="groq", api_key="k") == "ok"
    assert "prompt" in calls[0] and "prompt" not in calls[1]
    assert calls[2]["model"] == "whisper-large-v3-turbo"


def test_transcribe_error_message(monkeypatch):
    resp = SimpleNamespace(status_code=401, json=lambda: {"error": {"message": "Invalid API Key"}}, text="")
    monkeypatch.setattr(transcriber.requests, "post", lambda *a, **k: resp)
    with pytest.raises(transcriber.TranscriptionError, match="Invalid API Key"):
        transcriber.transcribe(b"x", provider="groq", api_key="k")


def test_prompt_echo_dropped():
    assert transcriber.strip_prompt_echo("สวัสดีครับ") == ""
    assert transcriber.strip_prompt_echo("ไปกินข้าว") == "ไปกินข้าว"


def test_single_instance(unused_port=47999):
    pytest.importorskip("tkinter")
    from speakaj import app

    assert app.acquire_single_instance(unused_port)
    first = app._instance_socket
    assert not app.acquire_single_instance(unused_port)
    first.close()


def test_setup_gui_env_roundtrip(tmp_path, monkeypatch):
    pytest.importorskip("tkinter")
    from speakaj import setup_gui

    monkeypatch.setattr(setup_gui, "CONFIG_DIR", tmp_path)
    setup_gui.write_env({"GROQ_API_KEY": "gsk_x", "ANTHROPIC_API_KEY": ""})
    assert setup_gui.read_env() == {"GROQ_API_KEY": "gsk_x"}
