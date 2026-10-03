"""Word counting, weekly usage stats, and dictation history."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from .config import CONFIG_DIR

STATS_FILE = CONFIG_DIR / "stats.json"
HISTORY_FILE = CONFIG_DIR / "history.jsonl"
HISTORY_LIMIT = 500

_LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*")
_THAI_RUN_RE = re.compile(r"[฀-๿]+")
# Thai is written without spaces between words; average Thai word length is
# roughly 4 characters, which is close enough for a usage counter.
THAI_CHARS_PER_WORD = 4


def count_words(text: str) -> int:
    words = len(_LATIN_WORD_RE.findall(text))
    for run in _THAI_RUN_RE.findall(text):
        words += max(1, round(len(run) / THAI_CHARS_PER_WORD))
    return words


def week_key(day: dt.date | None = None) -> str:
    year, week, _ = (day or dt.date.today()).isocalendar()
    return f"{year}-W{week:02d}"


class Stats:
    def __init__(self, path: Path = STATS_FILE):
        self.path = path
        self.data = {"week": week_key(), "week_words": 0, "total_words": 0, "dictations": 0}
        if path.is_file():
            try:
                self.data.update(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                pass
        self._roll_week()

    def _roll_week(self) -> None:
        current = week_key()
        if self.data.get("week") != current:
            self.data["week"] = current
            self.data["week_words"] = 0

    @property
    def week_words(self) -> int:
        self._roll_week()
        return int(self.data["week_words"])

    def add(self, words: int) -> None:
        self._roll_week()
        self.data["week_words"] += words
        self.data["total_words"] += words
        self.data["dictations"] += 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def over_limit(self, limit: int) -> bool:
        return limit > 0 and self.week_words >= limit


def append_history(raw: str, cleaned: str, seconds: float, path: Path = HISTORY_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": dt.datetime.now().isoformat(timespec="seconds"),
        "seconds": round(seconds, 1),
        "raw": raw,
        "text": cleaned,
    }
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    lines.append(json.dumps(entry, ensure_ascii=False))
    path.write_text("\n".join(lines[-HISTORY_LIMIT:]) + "\n", encoding="utf-8")


def last_history(path: Path = HISTORY_FILE) -> str:
    if not path.is_file():
        return ""
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        return ""
    return json.loads(lines[-1]).get("text", "")
