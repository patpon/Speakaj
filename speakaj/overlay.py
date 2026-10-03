"""Small always-on-top pill that shows recording / processing status.

Tk must run on the main thread, so other threads post updates through a
queue that the Tk loop polls.
"""

from __future__ import annotations

import queue
import sys
import tkinter as tk
from typing import Callable

BG = "#111827"
FG = "#F9FAFB"
ACCENT = {"listening": "#EF4444", "processing": "#3B82F6", "done": "#22C55E", "error": "#F59E0B"}
FONT = "Leelawadee UI" if sys.platform == "win32" else ("Thonburi" if sys.platform == "darwin" else "Noto Sans Thai")


class Overlay:
    def __init__(self, enabled: bool = True, level_source: Callable[[], float] | None = None):
        self.enabled = enabled
        self.level_source = level_source or (lambda: 0.0)
        self._queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self._hide_job = None
        self._state = "idle"

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", 0.93)
        except tk.TclError:
            pass
        self.root.configure(bg=BG)

        frame = tk.Frame(self.root, bg=BG, padx=14, pady=8)
        frame.pack()
        self.dot = tk.Canvas(frame, width=14, height=14, bg=BG, highlightthickness=0)
        self.dot.pack(side="left", padx=(0, 8))
        self.dot_id = self.dot.create_oval(2, 2, 12, 12, fill=ACCENT["listening"], outline="")
        self.label = tk.Label(frame, text="", bg=BG, fg=FG, font=(FONT, 11))
        self.label.pack(side="left")
        self.meter = tk.Canvas(frame, width=60, height=14, bg=BG, highlightthickness=0)
        self.meter.pack(side="left", padx=(10, 0))

        self.root.after(50, self._poll)

    # Thread-safe API -----------------------------------------------------
    def show(self, state: str, text: str) -> None:
        self._queue.put((state, text))

    def hide(self) -> None:
        self._queue.put(("idle", ""))

    def quit(self) -> None:
        self._queue.put(("quit", ""))

    # Tk thread -------------------------------------------------------------
    def _poll(self) -> None:
        try:
            while True:
                state, text = self._queue.get_nowait()
                if state == "quit":
                    self.root.quit()
                    return
                self._apply(state, text)
        except queue.Empty:
            pass
        if self._state == "listening":
            self._draw_meter(self.level_source())
        self.root.after(50, self._poll)

    def _apply(self, state: str, text: str) -> None:
        self._state = state
        if self._hide_job is not None:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None
        if state == "idle" or not self.enabled:
            self.root.withdraw()
            return
        self.dot.itemconfigure(self.dot_id, fill=ACCENT.get(state, FG))
        self.label.configure(text=text)
        if state == "listening":
            self.meter.pack(side="left", padx=(10, 0))
        else:
            self.meter.pack_forget()
        self._place()
        self.root.deiconify()
        self.root.lift()
        if state in ("done", "error"):
            self._hide_job = self.root.after(1800 if state == "done" else 4000, self.root.withdraw)

    def _place(self) -> None:
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w) // 2}+{sh - h - 90}")

    def _draw_meter(self, level: float) -> None:
        self.meter.delete("all")
        bars = 6
        lit = min(bars, int(level * 120))
        for i in range(bars):
            x = i * 10
            height = 4 + i * 2
            color = ACCENT["listening"] if i < lit else "#374151"
            self.meter.create_rectangle(x, 14 - height, x + 6, 14, fill=color, outline="")

    def run(self) -> None:
        self.root.mainloop()
