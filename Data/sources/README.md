# Preparing the brochure library

Place only the official brochures and documents you obtained in this folder or a brand-named subfolder. AutoSaarthi does not download or scrape them.

For every file, add one row to `../catalog.csv` with:

- `brand`, `model`, and `model_year` as written in the document; use `Not stated` when the brochure doesn't give a model year;
- `brochure_edition` for the date/version printed in the document, kept separate from model year;
- `market` for the country/region the document covers (for example, India or South Africa); use `Not stated` when unclear;
- `variant` as the named trim, or `All brochure variants` when the file covers several trims;
- `body_type` and `fuel_type` when the source states them;
- `active_in_india` as `yes` or `archive` only when you have confirmed that status; otherwise use `unknown`;
- `brochure_filename` matching the file's relative path under this folder (for example, `Hyundai/venue.pdf`); and
- `official_source_url` as the official webpage/PDF address when available.

Keep model years separate when the specifications differ. Do not treat a brochure's print/update date as the vehicle model year. Keep market-specific brochures separate because vehicle specifications can vary by country. If the official source does not state a value, enter `Not stated` or leave optional fields blank rather than guessing. Current/archive labels are declarations and are not independently verified by the app.

Supported files are PDFs with selectable text and DOCX documents. Scanned/image-only PDFs are not OCR-processed in this build. Run `python ingest_corpus.py` from the AutoSaarthi project folder to index the catalogue. An exact duplicate document is skipped; correct any metadata mistakes in the catalogue before indexing.
