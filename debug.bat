@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo ยังไม่ได้ติดตั้ง - กรุณารัน install.bat ก่อน
  pause
  exit /b 1
)
echo == ตรวจระบบ ==
.venv\Scripts\python.exe -m speakaj --check
echo.
echo == เปิดโปรแกรมแบบเห็นข้อความ (ปิดหน้าต่างนี้ = ปิดโปรแกรม) ==
.venv\Scripts\python.exe -m speakaj -v
pause
