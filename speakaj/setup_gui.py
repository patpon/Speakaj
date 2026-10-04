"""First-run window for entering API keys, used when there is no console
(the windowed .exe / .app), where the terminal prompts in --setup can't work."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import messagebox

from . import APP_NAME
from .config import CONFIG_DIR, load_config
from .overlay import FONT

BLUE = "#2563EB"
KEYS = [
    ("GROQ_API_KEY", "Groq API key (จำเป็น)", "https://console.groq.com/keys"),
    ("ANTHROPIC_API_KEY", "Anthropic API key (ไม่บังคับ)", "https://console.anthropic.com"),
]


def read_env() -> dict[str, str]:
    env_path = CONFIG_DIR / ".env"
    values: dict[str, str] = {}
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip()
    return values


def write_env(values: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / ".env").write_text(
        "".join(f"{k}={v}\n" for k, v in values.items() if v), encoding="utf-8"
    )


def run_setup_window() -> bool:
    """Show the setup window. Returns True if a way to transcribe was saved."""
    values = read_env()
    cfg = load_config()
    has_relay = bool(cfg.effective_relay_url())
    saved = {"ok": False}

    root = tk.Tk()
    root.title(f"{APP_NAME} — ตั้งค่า")
    root.configure(bg="white", padx=24, pady=20)
    root.resizable(False, False)

    tk.Label(root, text="แค่พูด ไม่ต้องพิมพ์", font=(FONT, 16, "bold"), bg="white", fg=BLUE).pack(anchor="w")
    tk.Label(
        root,
        text="ใส่รหัสทดลอง หรือ Groq API key ของคุณเอง อย่างใดอย่างหนึ่ง" if has_relay
        else "ใส่ Groq API key เพื่อแปลงเสียงเป็นข้อความ (ขอฟรี กดลิงก์ด้านล่าง)",
        font=(FONT, 10), bg="white", fg="#475569",
    ).pack(anchor="w", pady=(2, 14))

    demo = None
    if has_relay:
        tk.Label(root, text="รหัสทดลอง (เช่น DEMO-AB12-CD34)", font=(FONT, 10, "bold"), bg="white").pack(anchor="w")
        demo = tk.Entry(root, width=52, font=("Consolas", 12))
        demo.insert(0, cfg.demo_code)
        demo.pack(anchor="w", ipady=4, pady=(0, 6))
        tk.Label(root, text="— หรือ —", font=(FONT, 9), bg="white", fg="#94A3B8").pack(pady=(4, 8))

    entries = {}
    for key, label, url in KEYS:
        tk.Label(root, text=label, font=(FONT, 10, "bold"), bg="white").pack(anchor="w")
        entry = tk.Entry(root, width=52, show="•", font=(FONT, 10))
        entry.insert(0, values.get(key, ""))
        entry.pack(anchor="w", ipady=4)
        link = tk.Label(root, text=f"ขอ key ที่ {url}", font=(FONT, 9, "underline"), fg=BLUE, bg="white", cursor="hand2")
        link.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))
        link.pack(anchor="w", pady=(2, 12))
        entries[key] = entry

    tk.Label(
        root, text="กด Ctrl ขวา ค้างไว้แล้วพูด · ปล่อยเพื่อพิมพ์ · F9 = พูดยาวแบบไม่ต้องกดค้าง",
        font=(FONT, 9), bg="white", fg="#475569",
    ).pack(anchor="w", pady=(0, 12))

    def save():
        for key, entry in entries.items():
            values[key] = entry.get().strip()
        code = demo.get().strip().upper() if demo is not None else ""
        if not code and not values.get("GROQ_API_KEY"):
            messagebox.showwarning(
                APP_NAME, "กรุณาใส่รหัสทดลอง หรือ Groq API key" if has_relay else "กรุณาใส่ Groq API key", parent=root
            )
            return
        write_env(values)
        cfg = load_config()
        # A personal Groq key wins over a demo code when both are filled in.
        cfg.stt_provider = "groq" if values.get("GROQ_API_KEY") else "relay"
        cfg.demo_code = code
        cfg.save()
        saved["ok"] = True
        root.destroy()

    tk.Button(
        root, text="บันทึกและเริ่มใช้งาน", command=save, font=(FONT, 11, "bold"),
        bg=BLUE, fg="white", activebackground="#1D4ED8", activeforeground="white",
        relief="flat", padx=16, pady=6, cursor="hand2",
    ).pack(anchor="e")

    root.bind("<Return>", lambda _e: save())
    root.eval("tk::PlaceWindow . center")
    (demo or entries["GROQ_API_KEY"]).focus_set()
    root.mainloop()
    return saved["ok"]
