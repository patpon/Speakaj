"""Wires hotkeys, recorder, transcription, cleanup and text insertion together."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time

from . import APP_NAME, __version__, sounds
from .cleaner import clean
from .config import CONFIG_DIR, CONFIG_FILE, Config
from .hotkey import HotkeyListener
from .inserter import copy_to_clipboard, insert_text
from .overlay import Overlay
from .recorder import Recorder, is_silent, to_wav_bytes
from .stats import Stats, append_history, count_words, last_history
from .transcriber import TranscriptionError, transcribe

log = logging.getLogger(__name__)


def process_audio(cfg: Config, audio: bytes, filename: str = "speech.wav") -> tuple[str, str]:
    """Transcribe and clean one recording. Returns (raw, cleaned)."""
    raw = transcribe(
        audio,
        filename=filename,
        provider=cfg.stt_provider,
        api_key=cfg.api_key(cfg.stt_provider),
        model=cfg.stt_model,
        language=cfg.language,
        dictionary=cfg.dictionary,
    )
    return raw, clean(raw, cfg)


class SpeakajApp:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.stats = Stats()
        self.recorder = Recorder(cfg.sample_rate, cfg.max_record_seconds)
        self.overlay = Overlay(cfg.show_overlay, level_source=lambda: self.recorder.level)
        self.hotkeys = HotkeyListener(
            cfg.hotkey, cfg.toggle_hotkey, self.start_recording, self.stop_recording, self.cancel_recording
        )
        self._busy = threading.Lock()
        self._tray = None

    # Recording lifecycle ---------------------------------------------------
    def start_recording(self) -> None:
        if self.stats.over_limit(self.cfg.weekly_word_limit):
            self.overlay.show("error", f"ครบโควต้า {self.cfg.weekly_word_limit:,} คำ/สัปดาห์แล้ว")
            return
        try:
            self.recorder.start()
        except Exception as exc:
            log.exception("Cannot open microphone")
            self.overlay.show("error", f"เปิดไมค์ไม่ได้: {exc}")
            sounds.play("error", self.cfg.play_sounds)
            return
        sounds.play("start", self.cfg.play_sounds)
        self.overlay.show("listening", "กำลังฟัง…")

    def cancel_recording(self) -> None:
        if self.recorder.recording:
            self.recorder.stop()
        self.overlay.hide()

    def stop_recording(self) -> None:
        if not self.recorder.recording:
            return
        samples, seconds = self.recorder.stop()
        sounds.play("stop", self.cfg.play_sounds)
        if seconds < self.cfg.min_record_seconds or is_silent(samples):
            self.overlay.hide()
            return
        wav = to_wav_bytes(samples, self.cfg.sample_rate)
        threading.Thread(target=self._process, args=(wav, seconds), daemon=True).start()

    def _process(self, wav: bytes, seconds: float) -> None:
        with self._busy:
            self.overlay.show("processing", "กำลังแปลงเสียง…")
            started = time.monotonic()
            try:
                raw, text = process_audio(self.cfg, wav)
            except TranscriptionError as exc:
                log.error("%s", exc)
                self.overlay.show("error", str(exc)[:80])
                sounds.play("error", self.cfg.play_sounds)
                return
            if not text:
                self.overlay.hide()
                return
            if self.cfg.add_trailing_space and not text.endswith(("\n", " ")):
                text += " "
            try:
                insert_text(text, self.cfg.insert_mode, self.cfg.restore_clipboard)
            except Exception as exc:
                log.exception("Insert failed")
                copy_to_clipboard(text)
                self.overlay.show("error", f"วางข้อความไม่ได้ (คัดลอกไว้แล้ว): {exc}")
            words = count_words(text)
            self.stats.add(words)
            append_history(raw, text.strip(), seconds)
            elapsed = time.monotonic() - started
            self.overlay.show("done", f"✓ {words} คำ · {elapsed:.1f}s")
            self._refresh_tray()
            log.info("Dictated %d words in %.1fs (audio %.1fs)", words, elapsed, seconds)

    # Tray --------------------------------------------------------------------
    def _usage_text(self) -> str:
        limit = self.cfg.weekly_word_limit
        used = self.stats.week_words
        return f"สัปดาห์นี้: {used:,} / {limit:,} คำ" if limit else f"สัปดาห์นี้: {used:,} คำ"

    def _refresh_tray(self) -> None:
        if self._tray is not None:
            self._tray.update_menu()

    def _start_tray(self) -> None:
        # pystray needs the main thread on macOS, which Tk already owns there.
        if sys.platform == "darwin":
            return
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            return

        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((4, 4, 60, 60), fill=(37, 99, 235))
        d.rounded_rectangle((24, 14, 40, 38), radius=8, fill="white")
        d.arc((18, 24, 46, 46), 0, 180, fill="white", width=3)
        d.line((32, 46, 32, 52), fill="white", width=3)

        item = pystray.MenuItem
        menu = pystray.Menu(
            item(f"{APP_NAME} {__version__} · กด {self.cfg.hotkey} ค้างเพื่อพูด", None, enabled=False),
            item(lambda _: self._usage_text(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("คัดลอกข้อความล่าสุด", lambda: copy_to_clipboard(last_history())),
            item("เปิดไฟล์ตั้งค่า", lambda: _open_path(CONFIG_FILE)),
            item("เปิดโฟลเดอร์ประวัติ", lambda: _open_path(CONFIG_DIR)),
            pystray.Menu.SEPARATOR,
            item("ออก", self.quit),
        )
        self._tray = pystray.Icon(APP_NAME, img, APP_NAME, menu)
        self._tray.run_detached()

    def quit(self) -> None:
        self.hotkeys.stop()
        if self._tray is not None:
            self._tray.stop()
        self.overlay.quit()

    def run(self) -> None:
        self.hotkeys.start()
        self._start_tray()
        print(f"{APP_NAME} พร้อมแล้ว — กด [{self.cfg.hotkey}] ค้างไว้แล้วพูด, ปล่อยเพื่อพิมพ์ข้อความ")
        print(f"หรือกด [{self.cfg.toggle_hotkey}] เพื่อเริ่ม/หยุดแบบไม่ต้องกดค้าง · Ctrl+C เพื่อออก")
        try:
            self.overlay.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.quit()


def _open_path(path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)
