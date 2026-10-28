# AutoSaarthi India — Project and Viva Guide

## What the project does

AutoSaarthi is a document-grounded car research assistant for Indian vehicle buyers. It searches vehicle brochures and other documents that the project owner supplies, then uses the relevant passages to answer questions and compare cars. It is designed to avoid filling gaps with a language model's general memory.

The project can hold documents for up to roughly 180 models, but the library only covers the cars whose brochures have actually been supplied and indexed. The supplied Hyundai, Tata, Jeep, Toyota, Mahindra, Maruti Suzuki, Kia, Honda, Renault, MG, and Volkswagen PDFs are listed in the catalogue; most cover recent vehicles from 2020 onward, although model year is left unstated when the brochure does not establish it. Each catalogue entry records its market where known so specifications from India, South Africa, Indonesia, and New Zealand are not silently treated as interchangeable.

## The three parts of the website

1. **AI Assistant** — Ask questions about an indexed car, compare cars, or upload a PDF/DOCX and ask about it. Clear questions with a named car go directly to retrieval; local typo cleanup handles simple spelling slips. Gemini interprets uncertain questions, more difficult typos, and follow-up references. The assistant includes 100 predefined brochure question starters across specifications, EVs, safety, comfort, technology, variants, and comparisons. Select one or two cars from the built-in library, then choose a starter; these prompts search only the matching built-in brochures, even when uploaded documents are attached. Answers still use retrieved passages and citations. The upload flow identifies vehicle details from the document and attaches it to the current chat. For ordinary questions, attached brochures continue to constrain retrieval; without attachments, it searches the indexed library.
2. **Knowledge Base** — Search inside indexed brochure passages as well as filter documents by metadata. Results show short evidence excerpts and source locations. A document can be opened from its card or passage-search result.
3. **Official Portals** — Open manufacturer and government/safety websites in a new tab. AutoSaarthi does not scrape or automatically index those sites.

## How the RAG answer is made

```text
User-provided brochure
        ↓
Extract PDF text and page numbers; OCR scan-only pages locally, or extract DOCX text and table rows
        ↓
Split text into overlapping passages
        ↓
Create local sentence embeddings and store passages in Chroma
        ↓
Correct straightforward spelling locally; use Gemini for uncertain wording, harder typos, and follow-up references
        ↓
Find relevant passages for the named car(s), using MMR retrieval
        ↓
Send only those passages and the interpreted question to Gemini for a grounded answer
        ↓
Show a concise answer. The Knowledge Base lets the user inspect the original source separately.
```

The local embedding model is `sentence-transformers/all-MiniLM-L6-v2`. It is loaded once at app startup and reused; the app warms it before accepting questions so its model-load delay does not land on the first chat request. Gemini is configured through `GEMINI_API_KEY` and `GEMINI_MODEL` in the local `.env` file. When used, Gemini interprets the question before retrieval but is instructed not to supply vehicle facts during that step. The answer step receives retrieved brochure passages and must ground vehicle facts in those passages. Clear named-car queries and predefined prompts need one Gemini request for answer generation; ambiguous, typo-heavy, or follow-up queries need an additional interpretation request. Keep the key private and never commit it.

For a comparison, retrieval is performed separately for each named car so one car is less likely to take every result slot. MMR means *Maximal Marginal Relevance*: it balances relevance to the question with variety among the passages returned.

Chat retrieval returns up to six passages per car; its MMR candidate pool is 12 for one-car questions and 10 per car for comparisons. These values were checked against all 100 predefined prompts. Exact repeated requests can return the cached grounded answer only while the indexed brochure hashes and selected documents are unchanged. Warm local retrieval measured 116–160 ms in a small local benchmark; Gemini network generation is separate and cannot be guaranteed sub-second.

## What the assistant does when information is missing

- If a requested car/document is not in the indexed library, the app returns exactly: **“Sorry, I have no information about it.”**
- If the car is represented in the source passages but a requested specification is absent, the assistant should say **“Not stated in the supplied source.”** It must not guess.
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

1. Ask about a model that is not in the library and show the exact no-information response.
2. Upload an official brochure, fill in its car metadata, and wait for indexing to finish.
3. Ask a question whose answer appears in a supplied brochure, then check the corresponding document in the Knowledge Base.
4. Ask for a comparison between two indexed cars and show the side-by-side table and citations.
5. Open a manufacturer or safety portal from the Official Portals tab.

Use cars and questions that are actually supported by the brochures prepared for the demo. Do not claim that a model, specification, or source is covered until it appears in the app's Knowledge Base.

For a Windows demo, `start_app_windows.bat` launches the local app. Set `GEMINI_API_KEY` in the project's local `.env` file before demonstrating generated answers; do not paste the key into source code or commit it.

## Short viva explanation

> AutoSaarthi is a retrieval-augmented generation application for Indian vehicle documents. Gemini first interprets each question, including likely spelling mistakes and follow-up references. The system then retrieves relevant passages from user-supplied brochures, and Gemini answers from those passages. Question understanding is flexible, while vehicle facts remain restricted to the indexed evidence; if evidence is absent, the app says so instead of guessing.

