# AutoSaarthi continuation notes

Last updated: 28 October 2026

## Project location

`C:\Users\K M Rakshith Gowda\Documents\Codex\2026-10-27\hey-whats-p\outputs\AutoSaarthi`

## Changes made today

- Added a searchable question bank of 100 predefined brochure prompts in 10 categories. Prompts require selecting one built-in car, or two for comparisons; they skip Gemini question rewriting and search only matching built-in brochures, even if chat attachments are selected. Ordinary free-form questions retain the existing attached-document scope.
- Performance update: the sentence-transformer and Chroma store are initialized once behind a thread lock and warmed before the Flask server accepts chat requests. This moves the measured 28-second cold model load to startup; warm local retrieval measured 116–160 ms in a small sample.
- Added an in-memory LRU for repeated query embeddings, reduced MMR candidate pools to 12 (single car) and 10 per car (comparison) while retaining up to six/four final passages, and shortened generation context metadata without removing model/year/variant/fuel/market/edition scope.
- Reused Gemini HTTP clients, kept temperature at 0.0, shortened the system prompt, and added a response cache invalidated by corpus hashes, selected document IDs, and follow-up history. A cache-hit test confirmed identical grounded repeats skip both retrieval and generation. First-time Gemini latency remains dependent on Google's service/network.
- Rechecked all 100 predefined prompts after retrieval tuning: each returned passages for the expected car(s), with no empty retrievals or scope errors in the test set.
- Added exact prompt recognition for typed question-bank questions, a question-bank API endpoint, and a compact searchable/filterable question browser in the AI Assistant.
- Added local OCR fallback for scan-only PDF pages using Tesseract and PDFium, and began indexing 11 previously unsearchable source brochures. First-time OCR indexing can take several minutes.
- Removed the repeated hero title and eyebrow, removed the three extra suggestion chips, and removed message bubble backgrounds while keeping the AI icon box, the You marker, and comparison-table styling.
- Added a fast path for clear named-car questions so they skip the Gemini interpretation request. Questions with likely typos or follow-up references still use Gemini interpretation.
- Increased Gemini request timeouts and retries after question understanding failed during user testing; detailed failure tracebacks are now written to the launcher CMD window.
- Major update: Gemini now interprets and rewrites every chat question before retrieval, including likely spelling/typing errors and follow-up references. It uses attached vehicle names, the indexed catalogue, and recent chat context. The answer stage still receives retrieved brochure passages and must ground vehicle facts in those sources.
- Ambiguous or typo-heavy chat questions use two Gemini requests (interpretation, then answer generation); clear questions use one. Response time still depends on Google's API and network availability.
- Reduced the number of retrieved passages and shortened answer-generation limits to improve response time.
- Fixed single-car comparisons between attributes. For example, asking to compare a selected Venue's engine options and safety features should no longer be rejected as a request requiring two cars.
- Updated the greeting to: “Hello! Welcome to AutoSaarthi.”
- Updated the app version marker and script cache tag so a hard refresh loads recent changes.
- Updated the README and viva guide to describe Gemini question understanding and the current Gemini environment variables.
- Updated the intended chat source flow: attached brochures constrain retrieval to those documents; with none attached, retrieval uses the built-in library.
- Removed the Calculators navigation tab, page, and calculator JavaScript from the app.
- Changed the visual theme to warm parchment, ink, oxblood, and brass inspired by the supplied vintage-car reference.
- Replaced the low-contrast parchment colors after feedback with a dark espresso/black palette, warm ivory text, and amber accents; explicitly increased contrast on reference-library names, histories, and search previews. Latest CSS cache tag is `dark-vintage-motoring-20261028`.
- Compactified Knowledge Base passage previews by collapsing PDF whitespace, shortening excerpts, and clamping result cards.

## To see the latest changes

If the local server is running, stop it with `Ctrl+C`, start `start_app_windows.bat` again, and refresh the browser with `Ctrl+F5`.

## Resume checklist

- Continue a broader review of the assistant’s common question types, retrieval behavior, and answer grounding.
- Check the selected-brochure cases, typo correction fallback, one-car attribute comparisons, and multi-car comparisons against actual brochure text.
- Confirm Gemini question understanding works with the configured model and local API key, then check the rewritten queries preserve the user's intended car and requested facts.
- Review the vintage theme and compact search-result cards in the browser at desktop and mobile widths.
- No API key is recorded in this note. Keep the key only in the local `.env` file.

## Important limitation

The latest changes have not yet had a systematic end-to-end review against a prepared set of brochure questions. Answers must be checked against the supplied brochure pages; no project can guarantee a particular course mark.
