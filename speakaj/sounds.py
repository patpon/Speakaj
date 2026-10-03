"""Tiny start/stop cues so the user knows when the mic is live."""

from __future__ import annotations

import subprocess
import sys
import threading

_MAC_SOUNDS = {
    "start": "/System/Library/Sounds/Tink.aiff",
    "stop": "/System/Library/Sounds/Pop.aiff",
    "error": "/System/Library/Sounds/Basso.aiff",
}
_WIN_TONES = {"start": [(880, 60)], "stop": [(660, 60)], "error": [(220, 150), (180, 150)]}


def _play(kind: str) -> None:
    try:
        if sys.platform == "win32":
            import winsound

            for freq, ms in _WIN_TONES[kind]:
                winsound.Beep(freq, ms)
        elif sys.platform == "darwin":
            subprocess.run(["afplay", _MAC_SOUNDS[kind]], check=False, timeout=3)
    except Exception:
        pass


def play(kind: str, enabled: bool = True) -> None:
    if enabled:
        threading.Thread(target=_play, args=(kind,), daemon=True).start()
