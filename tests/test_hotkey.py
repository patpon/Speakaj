import pytest

pytest.importorskip("pynput.keyboard", exc_type=ImportError)  # also skips on headless Linux

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


def test_paste_key_is_layout_independent(monkeypatch):
    from speakaj import inserter

    monkeypatch.setattr(inserter.sys, "platform", "win32")
    assert inserter._paste_key().vk == 0x56
    monkeypatch.setattr(inserter.sys, "platform", "darwin")
    assert inserter._paste_key().vk == 9


def test_several_hold_keys():
    events = []
    h = hotkey.HotkeyListener(
        "ctrl_r, f8, not_a_key", "f9",
        on_start=lambda: events.append("start"),
        on_stop=lambda: events.append("stop"),
        on_cancel=lambda: events.append("cancel"),
    )
    h._on_press(Key.f8)
    h._on_release(Key.f8)
    h._on_press(Key.ctrl_r)
    h._on_release(Key.ctrl_r)
    assert events == ["start", "stop", "start", "stop"]
