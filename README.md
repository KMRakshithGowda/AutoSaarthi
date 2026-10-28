# AutoSaarthi India

An evidence-led automotive buyer guide built around official brochures and documents supplied by the project owner. It includes a Flask RAG assistant, dynamic PDF/DOCX ingestion, a searchable knowledge base, and official portal links.

## Current foundation

- Three sections: AI Assistant, Knowledge Base, and Official Portals.
- PDF and DOCX upload with brand, model, model year, brochure edition, market, variant, body type, fuel type, current/archive/unconfirmed India status, and optional official source URL. Local uploads are limited to 150 MB by default.
- Layout-aware PDF text extraction, DOCX paragraph and table extraction, chunking, the `all-MiniLM-L6-v2` embedding model through lightweight ONNX inference, and persistent Chroma storage.
- Per-model MMR retrieval for multi-vehicle questions, with source filename and PDF page / DOCX paragraph locators returned to the interface.
- Gemini question understanding on every chat request: corrects likely spelling/typing mistakes and resolves follow-up references before retrieval, using the selected brochures and indexed vehicle names as context.
- Semantic search across indexed brochure passages in the Knowledge Base, with source filename and page/section locators.
- Grounding prompt that rejects unsupported details and asks for a comparison table when appropriate.
- Immediate safety response for urgent brake, fire/smoke, and high-voltage battery warning queries, including when no source is indexed.
- Official portal links open in a new tab. The app does not crawl those sites.

Only user-provided documents are indexed. A missing model with no uploaded source receives exactly: `Sorry, I have no information about it.` An uploaded brochure can support an answer only from its extracted passages. Current/archive status is user-declared; otherwise it remains unconfirmed. The app does not independently verify sales status. Model year and brochure edition date are stored separately so a brochure print/update date is not mistaken for the vehicle model year. Market labels stay attached to retrieved passages so specifications from one country are not presented as another country's specifications.

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

On Windows, you can alternatively run `run_windows.bat`. It creates the environment, installs missing packages, creates `.env` only if it is absent, indexes the catalogue brochures, and starts the app. It never overwrites an existing `.env` file. The first indexing run can download the local embedding model.

Add an API key to `.env`:

```text
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Keep `.env` private. It is excluded from Git; never commit or share your API key.

Then start the app:

```powershell
python app.py
```

Open `http://127.0.0.1:8080`. The first document ingestion downloads the local embedding model. The local Chroma database and uploaded files are generated locally and are excluded from Git.

## Add the preloaded library

Place user-provided source documents in `Data/sources/` (brand subfolders are fine) and add one row per document to `Data/catalog.csv`. The `brochure_filename` value must match the relative path under `Data/sources/`. Then run:

```powershell
python ingest_corpus.py
```

You can also use the upload form for individual documents. Do not place confidential documents in the public repository.

## Important limits in this first build

- Scanned PDFs without an embedded text layer are not OCR-processed.
- Gemini rewrites each chat question before retrieval and can use recent turns to resolve follow-up references. Vehicle facts still come only from retrieved brochure passages.
- DOCX citations use paragraph locators because Word pagination can change across devices.
- India sales status is a user declaration or remains unconfirmed; it is not automatically verified.
- MMR helps diversify retrieval but does not guarantee equal evidence per vehicle. The system uses per-model filters when indexed model names are detected.
- A language model can still make mistakes. Check each cited source page before relying on a figure.
- Gemini model selection is configurable. Each normal chat answer uses Gemini for question understanding and again for grounded answer generation, so network speed and API availability affect response time.

## Render free preview deployment

The `render.yaml` and `Dockerfile` configure a free Render preview. The prebuilt Chroma index and `Data/manifest.json` are included in the deployment so preloaded brochure questions can use the indexed text without shipping the PDFs. The Knowledge Base searches and displays matching extracted passages with their brochure and page/section locator. The current local corpus has 92 manifest records, 93 PDF files, and an approximately 40 MB Chroma SQLite file.

This free preview has limits: live brochure uploads are disabled in the cloud; the local app keeps its uploader enabled. Render's free filesystem is temporary, so any upload or index changes made outside the deployed snapshot would disappear after a restart, sleep, or redeploy. The original PDFs are excluded from the deployment, so raw source downloads are unavailable online. Free services can also take about a minute to wake after inactivity. Keep `.env`, uploaded documents, and the raw source brochures out of GitHub. Add `GEMINI_API_KEY` as a secret environment variable in Render. See [Render's Flask deployment guide](https://render.com/docs/deploy-flask), [free service limits](https://render.com/docs/free), and [persistent disk options](https://render.com/docs/disks) if you later want permanent uploads and hosted PDFs.

## Portal links

`Data/portals.json` stores the official links. Update it if manufacturers change their pages or if additional companies are added.

