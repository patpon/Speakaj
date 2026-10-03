"""Insert text into the currently focused app."""

from __future__ import annotations

import sys
import threading
import time


def _paste_modifier():
    from pynput.keyboard import Key

    return Key.cmd if sys.platform == "darwin" else Key.ctrl


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
    with keyboard.pressed(_paste_modifier()):
        keyboard.press("v")
        keyboard.release("v")

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
