"""Global push-to-talk and toggle hotkeys."""

from __future__ import annotations

import time
from typing import Callable

# If another key is pressed this soon after the push-to-talk key, the user is
# typing a shortcut (e.g. Ctrl+C), not dictating, so the recording is cancelled.
SHORTCUT_GRACE_SECONDS = 0.4


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
        self.hold_key = parse_key(hold_key)
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
        if self._matches(key, self.hold_key):
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
        if self._mode == "hold" and self._matches(key, self.hold_key):
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
