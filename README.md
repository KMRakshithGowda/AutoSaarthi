# AutoSaarthi India

AutoSaarthi is a Flask-based RAG assistant for Indian vehicle research. It supports an active catalogue of 40 vehicles and has three website tabs: **AI Assistant**, **Knowledge Base**, and **Official Portals**.

## Sources and answers

The assistant retrieves from the active vehicle's indexed sources:

- Official manufacturer brochures (primary source for published specifications).
- Supplied YouTube review transcripts (reviewer and test-drive observations).
- Vehicle-specific extracts from the supplied Indian Buyer Guide and Comprehensive Expert & User Reviews Dataset Word documents. These are project-supplied summaries, not independently verified primary sources; their claims are labeled accordingly.

Gemini interprets spelling errors and follow-up references before retrieval, then drafts a concise answer from retrieved passages. The app distinguishes manufacturer specifications from review observations and project guide claims. It does not invent exact variant-specific figures when no source supports them. Unsupported or excluded vehicles use the configured fallback. Source references are shown with the answer.

## Local Windows setup

Requirements: Python 3.11+ and a Gemini API key.

1. Open Command Prompt in this project folder.
2. Double-click `run_windows.bat`. It installs dependencies if needed, indexes catalogue entries, then starts the server.
3. Add `GEMINI_API_KEY` to `.env` when prompted, close and rerun the launcher.
4. Open <http://127.0.0.1:8080> and leave the terminal window open while using the app.

The launcher now pauses and displays the error if setup/indexing/startup fails. If dependency installation is interrupted, resolve package-index/network access and run it again.

## Indexing sources

Run from this folder:

```bat
.venv\Scripts\python.exe prepare_buyer_guide.py
.venv\Scripts\python.exe ingest_corpus.py
```

The preparation script creates active-scope vehicle sections from both supplied Word guides. It deliberately skips duplicated, ambiguous, or excluded vehicle sections, and preserves the original DOCX files. Review `Data/catalog.csv` and `Data/project_scope.json` for source mapping and readiness.

For new sources, put them under `Data/sources/`, map the correct brand/model in `Data/catalog.csv` and active scope, then run `ingest_corpus.py`.

## Render deployment

The repository includes `render.yaml` and a Dockerfile for a Render preview. Configure `GEMINI_API_KEY` in Render's environment settings; never commit `.env` or API keys. Render uses a prebuilt Chroma index and disables live uploads. Only publish source documents you have permission to redistribute.

## Important limitations

This is a student project, not a professional automotive advisory service. PDFs and project guide values can be incomplete or inaccurate; check cited primary sources for safety, mileage, pricing, and variant-level claims. Website portals are external links and are not scraped into the local database.
