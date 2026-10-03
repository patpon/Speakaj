# Speakaj — แค่พูด ไม่ต้องพิมพ์

**Speakaj** คือโปรแกรมพิมพ์ด้วยเสียงสำหรับ Windows และ macOS รองรับ **ภาษาไทย + English** (พูดปนกันได้)
กดปุ่มค้าง → พูด → ปล่อย ข้อความที่เกลาแล้วจะถูกพิมพ์ลงในโปรแกรมที่เปิดอยู่ทันที — LINE, Word, Excel, Gmail, ChatGPT, Facebook ฯลฯ

> Desktop push-to-talk voice dictation for Windows & macOS. Hold a key, speak Thai or English, release — clean text is pasted into whatever app has focus.

🌐 Landing page: <https://patpon.github.io/Speakaj/> · ⬇️ Download: [Releases](https://github.com/patpon/Speakaj/releases)

---

## ✨ ความสามารถ / Features

| | |
|---|---|
| 🎙️ **Push-to-talk** | กด `Ctrl ขวา` ค้างไว้แล้วพูด ปล่อยแล้วพิมพ์ให้ |
| 🔁 **Hands-free** | กด `F9` ครั้งเดียวเริ่มอัด กดอีกครั้งหยุด (พูดยาวๆ ได้) |
| 🇹🇭 **ไทย + English** | ใช้ Whisper large-v3 แยกภาษาเองอัตโนมัติ |
| 🧹 **เกลาข้อความ** | Claude ตัดคำว่า "เอ่อ / อืม / um / uh" ใส่วรรคตอน แก้คำซ้ำ |
| 📋 **ใช้ได้ทุกโปรแกรม** | วางข้อความผ่าน clipboard แล้วคืนค่า clipboard เดิมให้ |
| 📊 **สถิติ** | นับจำนวนคำรายสัปดาห์ เก็บประวัติใน `~/.speakaj/history.jsonl` |
| 🔒 **เป็นส่วนตัว** | API key เก็บในเครื่องคุณเท่านั้น ไม่มี server กลาง |

---

## 🚀 ติดตั้ง / Install

### ตัวเลือก A — ดาวน์โหลดไฟล์สำเร็จรูป (ง่ายสุด)
1. ไปที่ [Releases](https://github.com/patpon/Speakaj/releases) ดาวน์โหลด
   - Windows: `Speakaj-windows.zip` → แตกไฟล์ → ดับเบิลคลิก `Speakaj.exe`
   - macOS: `Speakaj-macos.zip` → แตกไฟล์ → ลาก `Speakaj.app` ไปที่ Applications
2. ครั้งแรกจะถาม API key (ดูหัวข้อถัดไป)

### ตัวเลือก B — รันจาก source (ต้องมี Python 3.10+)

**Windows**
```bat
git clone https://github.com/patpon/Speakaj.git
cd Speakaj
install.bat      :: สร้าง venv + ติดตั้ง + ตั้งค่า API key
run.bat          :: เปิดโปรแกรม (ไม่มีหน้าต่างดำ)
debug.bat        :: ถ้าเปิดแล้วไม่มีอะไรเกิดขึ้น ใช้ตัวนี้ดู error
```

**macOS**
```bash
git clone https://github.com/patpon/Speakaj.git
cd Speakaj
chmod +x run.command install.command
./install.command   # สร้าง venv + ติดตั้ง + ตั้งค่า API key
./run.command       # หรือดับเบิลคลิกใน Finder
```

**คำสั่งอื่นๆ**
```bash
python -m speakaj --setup      # ตั้งค่า API key / ปุ่มลัดใหม่
python -m speakaj --check      # ตรวจ key และไมโครโฟน
python -m speakaj --file a.m4a # แปลงไฟล์เสียงเป็นข้อความ
```

---

## 🔑 ขอ API key

| Key | ใช้ทำอะไร | ขอได้ที่ | ค่าใช้จ่าย |
|---|---|---|---|
| `GROQ_API_KEY` | แปลงเสียงเป็นข้อความ (Whisper) | <https://console.groq.com/keys> | มี free tier |
| `ANTHROPIC_API_KEY` | เกลาข้อความด้วย Claude (ไม่บังคับ) | <https://console.anthropic.com> | จ่ายตามใช้ |
| `OPENAI_API_KEY` | ใช้แทน Groq ได้ (ไม่บังคับ) | <https://platform.openai.com/api-keys> | จ่ายตามใช้ |

ไม่มี Anthropic key ก็ใช้ได้ — โปรแกรมจะใช้ตัวกรองคำในเครื่องแทน

Key จะถูกเก็บที่ `~/.speakaj/.env` (Windows: `C:\Users\<ชื่อ>\.speakaj\.env`) ดูตัวอย่างที่ [`.env.example`](.env.example)

---

## ⚙️ ตั้งค่า `~/.speakaj/config.json`

| Field | Default | ความหมาย |
|---|---|---|
| `hotkey` | `"ctrl_r"` | ปุ่มกดค้างเพื่อพูด (`alt_r`, `f8`, `cmd_r` …) |
| `toggle_hotkey` | `"f9"` | ปุ่มเปิด/ปิดอัดแบบไม่ต้องกดค้าง (`""` = ปิด) |
| `stt_provider` | `"groq"` | `groq` หรือ `openai` |
| `language` | `""` | `""` = ตรวจภาษาอัตโนมัติ, `"th"`, `"en"` |
| `cleanup_with_claude` | `true` | ใช้ Claude เกลาข้อความ |
| `claude_model` | `"claude-opus-5-5"` | รุ่นของ Claude |
| `custom_instructions` | `""` | คำสั่งเพิ่ม เช่น `"ใช้ภาษาทางการ"` |
| `dictionary` | `[]` | คำเฉพาะ เช่น `["โกลด์เบรด", "Vansales"]` |
| `insert_mode` | `"paste"` | `paste` (เร็ว) หรือ `type` (จำลองพิมพ์) |
| `restore_clipboard` | `true` | คืนค่า clipboard เดิมหลังวาง |
| `play_sounds` / `show_overlay` | `true` | เสียงและแถบแสดงสถานะ |
| `weekly_word_limit` | `0` | โควต้าคำต่อสัปดาห์ (0 = ไม่จำกัด) |

แก้ไฟล์แล้ว ปิด-เปิดโปรแกรมใหม่

---

## 🍎 macOS: ต้องให้สิทธิ์ 3 อย่าง

**System Settings → Privacy & Security** แล้วเปิดสิทธิ์ให้ Terminal (ถ้ารันจาก source) หรือ Speakaj.app:

1. 🎤 **Microphone** — อัดเสียง
2. ♿ **Accessibility** — กด Cmd+V วางข้อความ
3. ⌨️ **Input Monitoring** — ฟังปุ่มลัด

ให้สิทธิ์แล้วต้องปิด-เปิดโปรแกรมใหม่ · บน Mac แนะนำเปลี่ยน `hotkey` เป็น `"alt_r"` (Option ขวา)

> ไฟล์ .app ยังไม่ได้ sign — ครั้งแรกให้ **คลิกขวา → Open** หรือรัน `xattr -dr com.apple.quarantine /Applications/Speakaj.app`

---

## 🪟 Windows: เปิดอัตโนมัติตอนเปิดเครื่อง

1. กด `Win + R` พิมพ์ `shell:startup` → Enter
2. คลิกขวา `run.bat` (หรือ `Speakaj.exe`) → **Create shortcut** → ย้าย shortcut ไปโฟลเดอร์ที่เปิดขึ้นมา

ถ้าจะใช้งานในโปรแกรมที่ Run as administrator ต้องเปิด Speakaj แบบ admin ด้วย

---

## 🛠️ แก้ปัญหา / Troubleshooting

| อาการ | วิธีแก้ |
|---|---|
| กดปุ่มแล้วไม่มีอะไรเกิดขึ้น | รัน `python -m speakaj --check -v` ดู error · Mac: เช็คสิทธิ์ Input Monitoring |
| อัดได้แต่ไม่พิมพ์ | Mac: เช็ค Accessibility · ลองตั้ง `insert_mode` เป็น `"type"` |
| ไม่มีไมค์ / `PortAudio` error | เช็คไมค์ใน Sound settings · Linux: `sudo apt install libportaudio2` |
| `401 Unauthorized` | API key ผิด → `python -m speakaj --setup` |
| `429 Rate limit` | Groq free tier เต็ม รอสักครู่ หรือเปลี่ยนเป็น `openai` |
| ภาษาไทยเพี้ยน | ตั้ง `"language": "th"` และใส่คำเฉพาะใน `dictionary` |
| Ctrl ขวา ชนกับโปรแกรมอื่น | เปลี่ยน `hotkey` เป็น `"f8"` หรือ `"alt_r"` |

Log อยู่ที่ `~/.speakaj/speakaj.log`

---

## 👩‍💻 สำหรับนักพัฒนา / Development

```bash
pip install -r requirements-dev.txt
pytest                    # รัน test
python build.py           # สร้าง dist/Speakaj(.exe/.app) ด้วย PyInstaller
```

โครงสร้าง: `recorder` (อัดเสียง) → `transcriber` (Groq/OpenAI Whisper) → `cleaner` (Claude) → `inserter` (วางข้อความ) · ควบคุมโดย `app.py` + `hotkey.py`

Release: push tag `v0.1.0` → GitHub Actions สร้างไฟล์ Windows/macOS ขึ้น Releases ให้อัตโนมัติ

## License

MIT
