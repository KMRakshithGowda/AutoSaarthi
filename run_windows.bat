@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating the AutoSaarthi Python environment...
  py -m venv .venv
  if errorlevel 1 goto :failed
)

".venv\Scripts\python.exe" -c "import flask, dotenv, openai, langchain_chroma, langchain_core, langchain_huggingface, langchain_text_splitters, sentence_transformers, pypdf, pypdfium2, pytesseract, PIL, docx" >nul 2>nul
if errorlevel 1 (
  echo Installing required packages. This may take several minutes...
  ".venv\Scripts\python.exe" -m ensurepip --upgrade
  if errorlevel 1 goto :failed
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :failed
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env. Add your Gemini API key there for generated answers. Restart the app after editing it.
)

echo Indexing the brochures listed in Data\catalog.csv. The first run may download the local embedding model...
".venv\Scripts\python.exe" ingest_corpus.py
if errorlevel 1 goto :failed

echo Starting AutoSaarthi at http://127.0.0.1:8080
".venv\Scripts\python.exe" app.py
goto :end

:failed
echo.
echo Setup failed. Check that Python is installed and that this computer can access the package index.
pause

:end
endlocal
