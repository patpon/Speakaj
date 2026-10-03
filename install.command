#!/bin/bash
cd "$(dirname "$0")"
echo "== ติดตั้ง Speakaj =="
python3 -m venv .venv || { echo "ไม่พบ python3 — brew install python"; exit 1; }
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt pyobjc-framework-Quartz
python -m speakaj --setup
python -m speakaj --check
echo
echo "เสร็จแล้ว! อย่าลืมให้สิทธิ์ Microphone / Accessibility / Input Monitoring"
echo "ดับเบิลคลิก run.command เพื่อเริ่มใช้งาน"
