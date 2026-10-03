"""User configuration stored as JSON in the user's home directory.

Environment variables (or a .env file next to the app) override API keys so
secrets never have to be written into config.json.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("SPEAKAJ_HOME", Path.home() / ".speakaj"))
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    # Push-to-talk key. Any pynput key name ("ctrl_r", "alt_r", "f8", ...) or a
    # single character. Hold to record, release to transcribe and type.
    hotkey: str = "ctrl_r"
    # Optional hands-free toggle key: press once to start, again to stop.
    toggle_hotkey: str = "f9"

    # Speech-to-text provider: "groq" (fast, free tier) or "openai".
    stt_provider: str = "groq"
    stt_model: str = ""  # empty = provider default
    # Language hint for Whisper. "" lets Whisper auto-detect, which handles
    # mixed Thai/English sentences best.
    language: str = ""

    # Text cleanup with Claude (removes filler words, fixes punctuation).
    # When disabled or no key is set, a fast local rule-based cleanup is used.
    cleanup_with_claude: bool = True
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "low"
    # Extra instructions appended to the cleanup prompt, e.g. a custom
    # vocabulary or tone ("use formal Thai", "my company is called ...").
    custom_instructions: str = ""

    # How text is inserted: "paste" (clipboard + Ctrl/Cmd+V, works everywhere)
    # or "type" (simulated keystrokes, slower).
    insert_mode: str = "paste"
    restore_clipboard: bool = True
    add_trailing_space: bool = True

    sample_rate: int = 16000
    min_record_seconds: float = 0.3
    max_record_seconds: float = 300.0
    play_sounds: bool = True
    show_overlay: bool = True

    # Weekly word quota shown in the tray/overlay (0 = unlimited).
    weekly_word_limit: int = 0

    # API keys (prefer env vars: GROQ_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY).
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    dictionary: list[str] = field(default_factory=list)

    def api_key(self, provider: str) -> str:
        env = {
            "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }[provider]
        return os.environ.get(env) or getattr(self, f"{provider}_api_key", "")

    def save(self, path: Path = CONFIG_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(path: Path = CONFIG_FILE) -> Config:
    _load_dotenv(Path.cwd() / ".env")
    _load_dotenv(CONFIG_DIR / ".env")

    cfg = Config()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        known = {f.name for f in fields(Config)}
        for key, value in data.items():
            if key in known:
                setattr(cfg, key, value)
    else:
        cfg.save(path)
    return cfg
