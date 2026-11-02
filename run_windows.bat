@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo AutoSaarthi India - local launcher
echo Project folder: %CD%
echo ============================================================

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher 'py' was not found. Install Python 3.11 or newer.
  goto :failed
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the AutoSaarthi Python environment...
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
)

".venv\Scripts\python.exe" -c "import flask, dotenv, openai, langchain_chroma, langchain_core, langchain_huggingface, langchain_text_splitters, fastembed, pypdf, pypdfium2, pytesseract, PIL, docx" >nul 2>nul
if errorlevel 1 (
  echo Installing required packages. Keep this window open...
  ".venv\Scripts\python.exe" -m ensurepip --upgrade
  if errorlevel 1 goto :failed
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :failed
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env. Add GEMINI_API_KEY to it, then run this launcher again.
)

set "PYTHONUNBUFFERED=1"
echo.
echo Indexing active catalogue sources. First run may take several minutes.
".venv\Scripts\python.exe" prepare_buyer_guide.py
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" ingest_corpus.py
if errorlevel 1 goto :failed

echo.
echo Starting AutoSaarthi at http://127.0.0.1:8080
echo Keep this window open while using the app. Press Ctrl+C to stop it.
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto :failed

echo.
echo AutoSaarthi has stopped.
pause
goto :end

:failed
set "FAIL_CODE=%ERRORLEVEL%"
if "%FAIL_CODE%"=="0" set "FAIL_CODE=1"
echo.
echo AutoSaarthi could not finish setup or start. Read the error above.
echo Exit code: %FAIL_CODE%
pause
exit /b %FAIL_CODE%

:end
endlocal
