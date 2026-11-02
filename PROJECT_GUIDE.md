# AutoSaarthi India — Project and Viva Guide

## What the project does

AutoSaarthi is an automotive research assistant for Indian vehicle buyers. It searches supplied manufacturer brochures, video-review transcripts, vehicle-specific extracts from a project-supplied buyer guide, and an expert/user-review summary. The two Word guides are project-supplied summaries, not independently verified sources. When a useful detail is absent, Gemini may add clearly labeled general automotive context; exact vehicle-, trim-, year-, or market-specific figures must not be invented.

The active scope contains 40 vehicle entries. `Data/project_scope.json` is the authoritative list of supported vehicles and exclusions; `Data/source_mapping.json` maps each active vehicle to its available sources. Only resources actually present and indexed can provide source-backed details. Market-specific specifications remain separate. The two guides have 40 numbered sections, but some are duplicates, grouped across models, or outside the active scope. Only safely mapped sections are indexed; Harrier EV, Punch EV, and Glanza have no matching section in either guide.

## The three parts of the website

1. **AI Assistant** — Ask questions about an indexed car, compare cars, or upload a PDF/DOCX and ask about it. Gemini interprets spelling mistakes and follow-ups; the retriever searches the active built-in library or the documents attached to the chat. Review transcripts carry a distinct source type from brochures. Buyer-guide and expert/user-review entries are labeled as project-supplied summaries, not verified independent reports or manufacturer-confirmed specifications. Answers cite source names and page, transcript timestamp, or source section where available. General context is labeled as not verified by the supplied documents.
2. **Knowledge Base** — Search indexed brochure, review-transcript, buyer-guide, and expert/user-review passages as well as filter documents by metadata. Results show short evidence excerpts and source locations. A document can be opened from its card or passage-search result.
3. **Official Portals** — Open manufacturer and government/safety websites in a new tab. AutoSaarthi does not scrape or automatically index those sites.

## How the RAG answer is made

```text
User-provided brochure, review transcript, or project guide
        ↓
Extract PDF text/pages, OCR scans locally, extract DOCX text/tables, parse timestamped TXT transcript lines, or split project guides into active vehicle-specific sections
        ↓
Split text into overlapping passages
        ↓
Create local sentence embeddings and store passages in Chroma
        ↓
Correct straightforward spelling locally; use Gemini for uncertain wording, harder typos, and follow-up references
        ↓
Find relevant passages for the named car(s), using MMR retrieval
        ↓
Send the interpreted question and retrieved passages to Gemini; label any added general context
        ↓
Show a concise answer. The Knowledge Base lets the user inspect the original source separately.
```

The embedding model is `sentence-transformers/all-MiniLM-L6-v2`, served through FastEmbed's lightweight ONNX runtime and loaded once on first retrieval. This keeps the hosted free instance's memory use lower while continuing to query the existing 384-dimensional Chroma index. Gemini is configured through `GEMINI_API_KEY` and `GEMINI_MODEL` in the local `.env` file. When used, Gemini interprets the question before retrieval but is instructed not to supply vehicle facts during that step. Official brochures ground manufacturer specifications; review transcripts provide reviewer observations; both project-supplied Word-guide sources are labeled as unverified summaries and cannot override a matching primary source. Clear named-car queries and predefined prompts need one Gemini request for answer generation; ambiguous, typo-heavy, or follow-up queries need an additional interpretation request. Keep the key private and never commit it.

For a comparison, retrieval is performed separately for each named car so one car is less likely to take every result slot. MMR means *Maximal Marginal Relevance*: it balances relevance to the question with variety among the passages returned.

Chat retrieval returns up to six passages per car; its MMR candidate pool is 12 for one-car questions and 10 per car for comparisons. These values were checked against all 100 predefined prompts. Exact repeated requests can return the cached grounded answer only while the indexed brochure hashes and selected documents are unchanged. Warm local retrieval measured 116–160 ms in a small local benchmark; Gemini network generation is separate and cannot be guaranteed sub-second.

## What the assistant does when information is missing

- If an exact figure is absent, the assistant avoids the “Not stated in the supplied source” dead end and may give clearly labeled general context. It must not invent exact trim-specific numbers.
- For unsupported or explicitly excluded models, the app returns the configured scope fallback rather than using general memory to invent vehicle-specific specifications.
- An uploaded archival brochure can still be queried. Its answer and citation are marked as archive material.
- Current/archive status is entered by the person adding the document; it can remain unconfirmed. AutoSaarthi does not independently confirm whether a model is currently sold.
- Urgent brake, fire/smoke, and high-voltage battery warning messages receive a short safety response before document search, even if the vehicle is not in the library.

## Honest limitations to mention in a presentation

- The project does not yet include the planned 180-car library; it needs the supplied brochures and catalogue rows first.
- Gemini can use recent turns and selected cars to interpret follow-ups such as “what about the other one?” before search. The model's interpretation can still be wrong; correct the query if it changes your intended car or specification.
- Scanned/image-only PDF pages are OCR-processed locally with Tesseract. OCR can misread stylized brochure text and complex tables; check the cited source page for important figures. Tesseract must be installed on the computer running the app.
- PDF extraction can misread complex brochure tables. Check the cited page for important figures.
- DOCX citations use paragraph or table-row locations, not page numbers, because Word pagination varies by device.
- Current/archive labels are user-declared, and portal links are shortcuts; neither is automatically verified or scraped.
- Brochure edition dates are not necessarily vehicle model years. The two are recorded separately where the brochure gives an edition date.
- This is an educational project, not professional automotive, financial, or safety advice.

## Suggested demo sequence

1. Select a supported car or ask about an attached vehicle source.
2. Compare a brochure specification with a review-transcript observation and show their separate citations.
3. Ask a question whose answer appears in a supplied brochure, then check the corresponding document in the Knowledge Base.
4. Ask for a comparison between two indexed cars and show the side-by-side table and citations.
5. Open a manufacturer or safety portal from the Official Portals tab.

Use cars and questions that are actually supported by the brochures prepared for the demo. Do not claim that a model, specification, or source is covered until it appears in the app's Knowledge Base.

For a Windows demo, `start_app_windows.bat` launches the local app. Set `GEMINI_API_KEY` in the project's local `.env` file before demonstrating generated answers; do not paste the key into source code or commit it.

## Short viva explanation

> AutoSaarthi is a retrieval-augmented generation application for Indian vehicle information. Gemini interprets the question, including likely spelling errors. The system retrieves brochure or review-transcript passages and shows their source. When exact source evidence is unavailable, the assistant labels general automotive context separately instead of presenting it as verified vehicle data.

