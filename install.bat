@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo == ติดตั้ง Speakaj ==
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% -m venv .venv || (echo ไม่พบ Python 3.10+  ดาวน์โหลดที่ https://www.python.org/downloads/ & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || (pause & exit /b 1)
python -m speakaj --setup
python -m speakaj --check
echo.
echo เสร็จแล้ว! ดับเบิลคลิก run.bat เพื่อเริ่มใช้งาน
pause
