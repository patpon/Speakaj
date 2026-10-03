"""Command-line entry point: `python -m speakaj`."""

from __future__ import annotations

import argparse
import getpass
import logging
import sys
from pathlib import Path

from . import APP_NAME, __version__
from .config import CONFIG_DIR, CONFIG_FILE, load_config


def _setup() -> None:
    """Interactive first-run setup that stores API keys in ~/.speakaj/.env."""
    env_path = CONFIG_DIR / ".env"
    existing = {}
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    print(f"== {APP_NAME} setup ==")
    print("Speech-to-text ใช้ Groq (ฟรี: https://console.groq.com/keys) หรือ OpenAI")
    print("Claude ใช้เกลาข้อความ ตัดคำว่า เอ่อ/อืม (https://console.anthropic.com) — เว้นว่างได้\n")
    for key, label in [
        ("GROQ_API_KEY", "Groq API key"),
        ("OPENAI_API_KEY", "OpenAI API key (ถ้าไม่ใช้ Groq)"),
        ("ANTHROPIC_API_KEY", "Anthropic API key"),
    ]:
        hint = " [มีอยู่แล้ว, Enter เพื่อข้าม]" if existing.get(key) else ""
        value = getpass.getpass(f"{label}{hint}: ").strip()
        if value:
            existing[key] = value

    cfg = load_config()
    if not existing.get("GROQ_API_KEY") and existing.get("OPENAI_API_KEY"):
        cfg.stt_provider = "openai"
    hotkey = input(f"ปุ่มกดค้างเพื่อพูด [{cfg.hotkey}]: ").strip()
    if hotkey:
        cfg.hotkey = hotkey
    cfg.save()

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("".join(f"{k}={v}\n" for k, v in existing.items() if v), encoding="utf-8")
    print(f"\nบันทึกแล้ว: {env_path} และ {CONFIG_FILE}")


def _transcribe_file(path: Path) -> None:
    from .app import process_audio

    cfg = load_config()
    raw, cleaned = process_audio(cfg, path.read_bytes(), path.name)
    print(f"raw    : {raw}")
    print(f"cleaned: {cleaned}")


def _check() -> int:
    cfg = load_config()
    ok = True
    print(f"{APP_NAME} {__version__} · config: {CONFIG_FILE}")
    for provider in ("groq", "openai", "anthropic"):
        print(f"  {provider:<9} key: {'✓' if cfg.api_key(provider) else '-'}")
    if not cfg.api_key(cfg.stt_provider):
        print(f"  ✗ ไม่มี API key ของ {cfg.stt_provider} (ใช้ `python -m speakaj --setup`)")
        ok = False
    try:
        import sounddevice as sd

        dev = sd.query_devices(kind="input")
        print(f"  mic: {dev['name']}")
    except Exception as exc:
        print(f"  ✗ mic: {exc}")
        ok = False
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="speakaj", description=f"{APP_NAME}: แค่พูด ไม่ต้องพิมพ์")
    parser.add_argument("--setup", action="store_true", help="ตั้งค่า API keys และปุ่มลัด")
    parser.add_argument("--check", action="store_true", help="ตรวจ API keys และไมโครโฟน")
    parser.add_argument("--file", type=Path, help="แปลงไฟล์เสียง (wav/mp3/m4a) แล้วพิมพ์ผลออกจอ")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    args = parser.parse_args(argv)

    # Windowed builds (pythonw / PyInstaller --windowed) have no console, so
    # always keep a log file the user can send when something goes wrong.
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.FileHandler(CONFIG_DIR / "speakaj.log", encoding="utf-8")]
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
    if args.setup:
        _setup()
        return 0
    if args.check:
        return _check()
    if args.file:
        _transcribe_file(args.file)
        return 0

    cfg = load_config()
    if not cfg.api_key(cfg.stt_provider):
        if sys.stdin is None or not sys.stdin.isatty():
            # Windowed build: no console to type into, so ask in a window.
            from .setup_gui import run_setup_window

            if not run_setup_window():
                return 1
            # Keys were written to ~/.speakaj/.env; load them into this process.
            from .config import _load_dotenv

            _load_dotenv(CONFIG_DIR / ".env")
        else:
            print("ยังไม่ได้ตั้ง API key — เริ่มตั้งค่าครั้งแรก\n")
            _setup()
        cfg = load_config()

    from .app import SpeakajApp

    SpeakajApp(cfg).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
