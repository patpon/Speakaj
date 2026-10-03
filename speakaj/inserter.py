"""Insert text into the currently focused app."""

from __future__ import annotations

import sys
import threading
import time


def _paste_modifier():
    from pynput.keyboard import Key

    return Key.cmd if sys.platform == "darwin" else Key.ctrl


def _paste_key():
    """The physical V key. Pressing the character "v" fails when a non-Latin
    layout (e.g. Thai Kedmanee) is active: pynput can't find "v" on that layout
    and types it as a unicode character, so Ctrl+V never reaches the app."""
    from pynput.keyboard import KeyCode

    if sys.platform == "win32":
        return KeyCode.from_vk(0x56)  # VK_V
    if sys.platform == "darwin":
        return KeyCode.from_vk(9)  # kVK_ANSI_V
    return "v"


def insert_text(text: str, mode: str = "paste", restore_clipboard: bool = True) -> None:
    if not text:
        return
    from pynput.keyboard import Controller

    keyboard = Controller()
    if mode == "type":
        keyboard.type(text)
        return

    import pyperclip

    previous = None
    if restore_clipboard:
        try:
            previous = pyperclip.paste()
        except pyperclip.PyperclipException:
            previous = None

    pyperclip.copy(text)
    time.sleep(0.05)
    key = _paste_key()
    with keyboard.pressed(_paste_modifier()):
        keyboard.press(key)
        keyboard.release(key)

    if previous is not None:
        # Give the target app time to read the clipboard before restoring it.
        def restore():
            time.sleep(0.6)
            try:
                if pyperclip.paste() == text:
                    pyperclip.copy(previous)
            except pyperclip.PyperclipException:
                pass

        threading.Thread(target=restore, daemon=True).start()


def copy_to_clipboard(text: str) -> None:
    import pyperclip

    pyperclip.copy(text)
