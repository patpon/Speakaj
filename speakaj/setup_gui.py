"""First-run window for entering API keys, used when there is no console
(the windowed .exe / .app), where the terminal prompts in --setup can't work."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import messagebox

from . import APP_NAME
from .config import CONFIG_DIR, load_config
from .hotkey import HOLD_KEY_CHOICES, split_keys
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
        text="ใส่รหัสทดลองที่ได้รับ แล้วกดบันทึก" if has_relay
        else "ใส่ Groq API key เพื่อแปลงเสียงเป็นข้อความ (ขอฟรี กดลิงก์ด้านล่าง)",
        font=(FONT, 10), bg="white", fg="#475569",
    ).pack(anchor="w", pady=(2, 14))

    demo = None
    if has_relay:
        tk.Label(root, text="รหัสทดลอง (เช่น DEMO-AB12-CD34)", font=(FONT, 10, "bold"), bg="white").pack(anchor="w")
        demo = tk.Entry(root, width=34, font=("Consolas", 13), justify="center")
        demo.insert(0, cfg.demo_code)
        demo.pack(anchor="w", ipady=6, pady=(2, 12), fill="x")

    # With a demo relay the key fields are optional, so they start hidden
    # behind a link; without one they are the only way in and always show.
    keys_frame = tk.Frame(root, bg="white")
    entries = {}
    for key, label, url in KEYS:
        if has_relay:
            label = label.replace("(จำเป็น)", "(ไม่บังคับ)")
        tk.Label(keys_frame, text=label, font=(FONT, 10, "bold"), bg="white").pack(anchor="w")
        entry = tk.Entry(keys_frame, width=52, show="•", font=(FONT, 10))
        entry.insert(0, values.get(key, ""))
        entry.pack(anchor="w", ipady=4, fill="x")
        link = tk.Label(keys_frame, text=f"ขอ key ที่ {url}", font=(FONT, 9, "underline"), fg=BLUE, bg="white", cursor="hand2")
        link.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))
        link.pack(anchor="w", pady=(2, 12))
        entries[key] = entry

    # Hold-to-talk keys: any ticked key works, so keyboards without a right
    # Ctrl (many compact and wireless ones) can still push-to-talk.
    keys_box = tk.Frame(root, bg="white")
    tk.Label(keys_box, text="ปุ่มกดค้างเพื่อพูด (เลือกได้หลายปุ่ม)", font=(FONT, 10, "bold"), bg="white").pack(anchor="w")
    row = tk.Frame(keys_box, bg="white")
    row.pack(anchor="w", pady=(2, 0))
    current = set(split_keys(cfg.hotkey))
    key_vars = {}
    for name, label in HOLD_KEY_CHOICES:
        var = tk.BooleanVar(value=name in current)
        tk.Checkbutton(row, text=label, variable=var, font=(FONT, 10), bg="white",
                       activebackground="white", highlightthickness=0).pack(side="left", padx=(0, 14))
        key_vars[name] = var
    tk.Label(keys_box, text="F9 = กดครั้งเดียวเริ่มพูด กดอีกครั้งหยุด (ใช้ได้เสมอ) · F8 ชนกับ Excel · Scroll Lock จะสลับไฟ",
             font=(FONT, 8), bg="white", fg="#64748B").pack(anchor="w", pady=(2, 0))

    hint = tk.Label(
        root, text="กดปุ่มที่เลือกค้างไว้แล้วพูด · ปล่อยเพื่อพิมพ์ข้อความ",
        font=(FONT, 9), bg="white", fg="#475569",
    )
    if has_relay and not any(values.get(k) for k, _l, _u in KEYS):
        toggle = tk.Label(root, text="มี API key ของตัวเอง? คลิกที่นี่", font=(FONT, 9, "underline"),
                          fg="#64748B", bg="white", cursor="hand2")

        def show_keys(_e=None):
            toggle.pack_forget()
            keys_frame.pack(anchor="w", fill="x", before=keys_box)
            root.eval("tk::PlaceWindow . center")

        toggle.bind("<Button-1>", show_keys)
        toggle.pack(anchor="w", pady=(0, 12))
    else:
        keys_frame.pack(anchor="w", fill="x")
    keys_box.pack(anchor="w", fill="x", pady=(0, 14))
    hint.pack(anchor="w", pady=(0, 12))

    def save():
        for key, entry in entries.items():
            values[key] = entry.get().strip()
        code = demo.get().strip().upper() if demo is not None else ""
        chosen = [name for name, var in key_vars.items() if var.get()]
        if not chosen:
            messagebox.showwarning(APP_NAME, "กรุณาเลือกปุ่มกดค้างอย่างน้อย 1 ปุ่ม", parent=root)
            return
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
        cfg.hotkey = ",".join(chosen)
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
