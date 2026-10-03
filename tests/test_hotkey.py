import pytest

pytest.importorskip("pynput")

from pynput.keyboard import Key, KeyCode  # noqa: E402

from speakaj import hotkey  # noqa: E402


def make(events):
    return hotkey.HotkeyListener(
        "ctrl_r",
        "f9",
        on_start=lambda: events.append("start"),
        on_stop=lambda: events.append("stop"),
        on_cancel=lambda: events.append("cancel"),
    )


def test_parse_key():
    assert hotkey.parse_key("ctrl_r") == Key.ctrl_r
    assert hotkey.parse_key("x") == KeyCode.from_char("x")
    assert hotkey.parse_key("") is None
    with pytest.raises(ValueError):
        hotkey.parse_key("not_a_key")


def test_hold_to_talk_ignores_autorepeat():
    events = []
    h = make(events)
    h._on_press(Key.ctrl_r)
    h._on_press(Key.ctrl_r)
    h._on_release(Key.ctrl_r)
    assert events == ["start", "stop"]


def test_shortcut_cancels():
    events = []
    h = make(events)
    h._on_press(Key.ctrl_r)
    h._on_press(KeyCode.from_char("c"))
    h._on_release(Key.ctrl_r)
    assert events == ["start", "cancel"]


def test_toggle():
    events = []
    h = make(events)
    h._on_press(Key.f9)
    h._on_press(KeyCode.from_char("a"))  # typing during toggle mode is fine
    h._on_press(Key.f9)
    assert events == ["start", "stop"]
