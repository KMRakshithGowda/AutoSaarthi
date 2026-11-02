# Preparing the brochure library

Place official brochures and review materials you obtained in this folder or a brand-named subfolder. AutoSaarthi does not download or scrape them. YouTube transcripts supplied by the project owner can be stored under `Reviews/`; they are indexed as reviewer/real-world observations, separate from official brochure claims.

For every file, add one row to `../catalog.csv` with:

- `brand`, `model`, and `model_year` as written in the document; use `Not stated` when the brochure doesn't give a model year;
- `brochure_edition` for the date/version printed in the document, kept separate from model year;
- `market` for the country/region the document covers (for example, India or South Africa); use `Not stated` when unclear;
- `variant` as the named trim, or `All brochure variants` when the file covers several trims;
- `body_type` and `fuel_type` when the source states them;
- `active_in_india` as `yes` or `archive` only when you have confirmed that status; otherwise use `unknown`;
- `brochure_filename` matching the file's relative path under this folder (for example, `Hyundai/venue.pdf`); and
- `official_source_url` as the official webpage/PDF address when available.
- `source_type` as `official_brochure` for a manufacturer brochure, `youtube_transcript` for a video transcript, `buyer_guide` for a project-supplied buyer guide, or `expert_user_reviews` for the project-supplied expert/user review summary. Project guides and reviews are not treated as independently verified sources.

Keep model years separate when the specifications differ. Do not treat a brochure's print/update date as the vehicle model year. Keep market-specific brochures separate because vehicle specifications can vary by country. If the official source does not state a value, enter `Not stated` or leave optional fields blank rather than guessing. Current/archive labels are declarations and are not independently verified by the app.

Supported source files are PDFs, DOCX documents, UTF-8 TXT transcripts, and Markdown transcripts. Transcript timestamps are preserved as source locators when the text lines begin with a timestamp. Scanned/image-only PDFs use the local OCR fallback when available. Run `python ingest_corpus.py` from the AutoSaarthi project folder to index active-catalogue entries. An exact duplicate source/entity pair is skipped; a comparison transcript can be mapped to more than one vehicle. `Data/project_scope.json` controls which built-in cars and documents are active in the application.
