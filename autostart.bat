@echo off
rem Double-click: Speakaj starts automatically when Windows starts.
rem Run again: asks to turn autostart off.
cd /d "%~dp0"
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Speakaj.lnk"

if exist "%LNK%" (
  choice /m "Autostart is ON. Turn it OFF"
  if errorlevel 2 exit /b 0
  del "%LNK%"
  echo Autostart OFF.
  pause
  exit /b 0
)

if not exist .venv\Scripts\pythonw.exe (
  echo Speakaj is not installed yet. Please run install.bat first.
  pause
  exit /b 1
)

powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK); $s.TargetPath='%~dp0.venv\Scripts\pythonw.exe'; $s.Arguments='-m speakaj'; $s.WorkingDirectory='%~dp0'; $s.Description='Speakaj voice dictation'; $s.Save()"
if exist "%LNK%" (
  echo Done! Speakaj will start automatically every time Windows starts.
  echo Run autostart.bat again to turn it off.
) else (
  echo Failed to create shortcut.
)
pause
