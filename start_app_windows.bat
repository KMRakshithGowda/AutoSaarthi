@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo AutoSaarthi is not set up yet. Run run_windows.bat once first.
  pause
  goto :end
)

echo Starting AutoSaarthi at http://127.0.0.1:8080
echo Keep this window open while using the app. Press Ctrl+C to stop it.
".venv\Scripts\python.exe" app.py

:end
endlocal
