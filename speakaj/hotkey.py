"""Global push-to-talk and toggle hotkeys."""

from __future__ import annotations

import logging
import sys
import time
from typing import Callable

# If another key is pressed this soon after the push-to-talk key, the user is
# typing a shortcut (e.g. Ctrl+C), not dictating, so the recording is cancelled.
SHORTCUT_GRACE_SECONDS = 0.4

# Hold-to-talk keys offered in the setup window, with the names people see.
# Several can be active at once ("ctrl_r,pause"), for keyboards that lack one.
HOLD_KEY_CHOICES = [
    ("ctrl_r", "Ctrl ขวา"),
    ("pause", "Pause"),
    ("scroll_lock", "Scroll Lock"),
    ("f8", "F8"),
]
KEY_LABELS = dict(HOLD_KEY_CHOICES) | {"alt_r": "Alt ขวา", "f9": "F9", "cmd_r": "Cmd ขวา"}
if sys.platform == "darwin":  # Mac keyboards have no Pause / Scroll Lock
    HOLD_KEY_CHOICES = [c for c in HOLD_KEY_CHOICES if c[0] not in ("pause", "scroll_lock")]

log = logging.getLogger(__name__)


def _parse_known(names: str) -> list:
    """Parse each key name, skipping ones this platform doesn't have (the
    default "ctrl_r,pause" must still start on a Mac)."""
    keys = []
    for name in split_keys(names):
        try:
            key = parse_key(name)
        except ValueError:
            log.warning("Hotkey %r is not available on this platform; ignoring it", name)
            continue
        if key is not None:
            keys.append(key)
    return keys


def split_keys(names: str) -> list[str]:
    return [n.strip().lower() for n in names.split(",") if n.strip()]


def describe_keys(names: str) -> str:
    """'ctrl_r,pause' -> 'Ctrl ขวา / Pause' for menus and hints."""
    return " / ".join(KEY_LABELS.get(n, n.upper() if len(n) > 1 else n) for n in split_keys(names))


def parse_key(name: str):
    from pynput.keyboard import Key, KeyCode

    name = name.strip().lower()
    if not name:
        return None
    if hasattr(Key, name):
        return getattr(Key, name)
    if len(name) == 1:
        return KeyCode.from_char(name)
    raise ValueError(f"Unknown key name: {name!r}")


class HotkeyListener:
    def __init__(
        self,
        hold_key: str,
        toggle_key: str,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_cancel: Callable[[], None],
    ):
        self.hold_keys = _parse_known(hold_key)
        self.toggle_key = parse_key(toggle_key)
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_cancel = on_cancel
        self._mode: str | None = None  # "hold" | "toggle" | None
        self._pressed_at = 0.0
        self._listener = None

    def _matches(self, key, target) -> bool:
        if target is None:
            return False
        if key == target:
            return True
        return getattr(key, "char", None) is not None and getattr(target, "char", None) == key.char

    def _on_press(self, key):
        if any(self._matches(key, k) for k in self.hold_keys):
            if self._mode is None:  # ignore key auto-repeat
                self._mode = "hold"
                self._pressed_at = time.monotonic()
                self.on_start()
            return
        if self._matches(key, self.toggle_key):
            if self._mode is None:
                self._mode = "toggle"
                self.on_start()
            elif self._mode == "toggle":
                self._mode = None
                self.on_stop()
            return
        if self._mode == "hold" and time.monotonic() - self._pressed_at < SHORTCUT_GRACE_SECONDS:
            self._mode = None
            self.on_cancel()

    def _on_release(self, key):
        if self._mode == "hold" and any(self._matches(key, k) for k in self.hold_keys):
            self._mode = None
            self.on_stop()

    def start(self) -> None:
        from pynput import keyboard

        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
