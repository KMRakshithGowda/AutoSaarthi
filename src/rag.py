"""Document ingestion and grounded retrieval for AutoSaarthi."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastembed import TextEmbedding
import pypdfium2 as pdfium
import pytesseract
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Data"
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(DATA_DIR / "uploads")))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", str(ROOT / "chroma_db")))
MANIFEST_PATH = Path(os.getenv("MANIFEST_PATH", str(DATA_DIR / "manifest.json")))
if not UPLOAD_DIR.is_absolute():
    UPLOAD_DIR = ROOT / UPLOAD_DIR
if not CHROMA_DIR.is_absolute():
    CHROMA_DIR = ROOT / CHROMA_DIR
if not MANIFEST_PATH.is_absolute():
    MANIFEST_PATH = ROOT / MANIFEST_PATH
COLLECTION = "autosaarthi"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FALLBACK = "Sorry, I have no information about it."

_embeddings = None
_cached_embeddings = None
_store = None
_store_lock = threading.Lock()
_ingestion_lock = threading.RLock()


class QueryCachedEmbeddings(Embeddings):
    """Delegate document vectors and memoize recent query vectors in memory."""

    def __init__(self, embeddings: Embeddings):
        self._embed_documents = embeddings.embed_documents
        self._embed_query_cached = lru_cache(maxsize=512)(embeddings.embed_query)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed_query_cached(text)


class FastEmbedEmbeddings(Embeddings):
    """Use the same MiniLM-L6-v2 vectors through lightweight ONNX inference."""

    def __init__(self, model: TextEmbedding):
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.embed(texts, batch_size=8)]

    def embed_query(self, text: str) -> list[float]:
        return next(self.model.query_embed(text)).tolist()


def _manifest() -> dict[str, Any]:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"documents": []}


def _save_manifest(data: dict[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = MANIFEST_PATH.with_suffix(".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, MANIFEST_PATH)
    finally:
        temporary_path.unlink(missing_ok=True)


def _store_instance() -> Chroma:
    global _store, _embeddings, _cached_embeddings
    if _store is None:
        with _store_lock:
            if _store is None:
                cache_dir = os.getenv("FASTEMBED_CACHE_PATH") or None
                _embeddings = FastEmbedEmbeddings(
                    TextEmbedding(
                        model_name=EMBEDDING_MODEL,
                        cache_dir=cache_dir,
                        threads=1,
                        enable_cpu_mem_arena=False,
                    )
                )
                _cached_embeddings = QueryCachedEmbeddings(_embeddings)
                _store = Chroma(
                    collection_name=COLLECTION,
                    embedding_function=_cached_embeddings,
                    persist_directory=str(CHROMA_DIR),
                )
    return _store


def warmup() -> None:
    """Load the local embedding model and persistent vector index before serving chats."""
    if list_documents():
        _store_instance()


def _read_pdf(path: Path) -> list[tuple[str, str]]:
    reader = PdfReader(str(path))
    pages = []
    pdfium_document = None
    try:
        for i, page in enumerate(reader.pages):
            try:
                # Layout mode keeps columns and many brochure tables more readable.
                text = page.extract_text(extraction_mode="layout") or ""
            except TypeError:
                text = page.extract_text() or ""
            if not text.strip():
                if pdfium_document is None:
                    configured_tesseract = os.getenv("TESSERACT_CMD", "").strip()
                    tesseract = (
                        configured_tesseract if configured_tesseract and Path(configured_tesseract).is_file()
                        else shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                    )
                    if not Path(tesseract).is_file():
                        raise RuntimeError("This scanned PDF needs local Tesseract OCR. Install Tesseract or set TESSERACT_CMD.")
                    pytesseract.pytesseract.tesseract_cmd = tesseract
                    pdfium_document = pdfium.PdfDocument(str(path))
                pdfium_page = pdfium_document[i]
                bitmap = pdfium_page.render(scale=2.5)
                image = bitmap.to_pil()
                try:
                    text = pytesseract.image_to_string(image, lang="eng", config="--psm 6") or ""
                finally:
                    image.close()
                    bitmap.close()
                    pdfium_page.close()
            pages.append((text, str(i + 1)))
    finally:
        if pdfium_document is not None:
            pdfium_document.close()
    return pages


def _read_docx(path: Path) -> list[tuple[str, str]]:
    doc = DocxDocument(str(path))
    # Preserve body order and include actual table rows; brochures often store
    # dimensions, powertrains, and variant equipment in tables.
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P

    extracted: list[tuple[str, str]] = []
    paragraph_no = table_no = 0
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            paragraph_no += 1
            paragraph = DocxParagraph(child, doc)
            if paragraph.text.strip():
                extracted.append((paragraph.text.strip(), f"paragraph {paragraph_no}"))
        elif isinstance(child, CT_Tbl):
            table_no += 1
            table = DocxTable(child, doc)
            rows = []
            for row_no, row in enumerate(table.rows, 1):
                cells = [" ".join(cell.text.split()) for cell in row.cells]
                line = " | ".join(cell for cell in cells if cell)
                if line.strip(" |"):
                    rows.append((row_no, line))
            group: list[tuple[int, str]] = []
            length = 0
            for row_no, line in rows:
                if group and length + len(line) > 450:
                    extracted.append(("\n".join(text for _, text in group), f"table {table_no}, rows {group[0][0]}-{group[-1][0]}"))
                    group, length = [], 0
                group.append((row_no, line))
                length += len(line) + 1
            if group:
                extracted.append(("\n".join(text for _, text in group), f"table {table_no}, rows {group[0][0]}-{group[-1][0]}"))
    return extracted


def _infer_upload_details(path: Path, extracted: list[tuple[str, str]], supplied: dict[str, str], display_filename: str | None = None) -> dict[str, str]:
    """Fill optional upload metadata from the filename and opening document text."""
    catalog = list_documents()
    filename = Path(display_filename or path.name).stem.replace("_", " ").replace("-", " ")
    opening_text = " ".join(text for text, _locator in extracted[:6])[:12000]
    haystack = f"{filename}\n{opening_text}"

    model_record = None
    for scope in (filename, haystack):
        matches = [d for d in catalog if d.get("model") and re.search(_phrase_pattern(d["model"]), scope, re.I)]
        if matches:
            model_record = max(matches, key=lambda d: len(d.get("model", "")))
            break

    brand = (supplied.get("brand") or "").strip()
    model = (supplied.get("model") or "").strip()
    if model_record:
        brand = brand or model_record.get("brand", "")
        model = model or model_record.get("model", "")

    brands = sorted({d.get("brand", "") for d in catalog if d.get("brand")}, key=len, reverse=True)
    if not brand:
        brand = next((candidate for candidate in brands if re.search(_phrase_pattern(candidate), haystack, re.I)), "")

    year = (supplied.get("model_year") or "").strip()
    if not year:
        year_match = re.search(r"\b(?:19|20)\d{2}\b", filename)
        year = year_match.group(0) if year_match else "Not stated"

    if not model:
        cleaned = re.sub(r"\b(?:brochure|e brochure|ebrochure|catalogue|catalog|specifications|specification|india|launch|edition|master|new|all)\b", " ", filename, flags=re.I)
        cleaned = re.sub(r"\b(?:19|20)\d{2}\b", " ", cleaned)
        cleaned = " ".join(cleaned.split())
        if brand:
            cleaned = re.sub(_phrase_pattern(brand), " ", cleaned, flags=re.I)
            cleaned = " ".join(cleaned.split())
        model = cleaned.title() or "Uploaded Vehicle"
    if not brand:
        # Keep an identifiable catalogue entry for a newly supplied model even
        # when the brand is not clear in the brochure text.
        brand = "Uploaded"

    inferred = {
        "brand": brand,
        "model": model,
        "model_year": year,
        "brochure_edition": (supplied.get("brochure_edition") or "").strip() or "Not stated",
        "market": (supplied.get("market") or "").strip() or "Not stated",
        "variant": (supplied.get("variant") or "").strip() or "Not specified",
        "body_type": (supplied.get("body_type") or "").strip() or "Not specified",
        "fuel_type": (supplied.get("fuel_type") or "").strip() or "Not specified",
        "active_in_india": supplied.get("active_in_india", "unknown") or "unknown",
    }
    return inferred


def ingest_file(
    path: Path,
    details: dict[str, str],
    official_url: str = "",
    display_filename: str | None = None,
) -> dict[str, Any]:
    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    with _ingestion_lock:
        existing = next((d for d in _manifest()["documents"] if d.get("sha256") == file_hash), None)
        if existing:
            return {**existing, "already_indexed": True}

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        extracted = _read_pdf(path)
    elif suffix == ".docx":
        extracted = _read_docx(path)
    else:
        raise ValueError("Upload a PDF or DOCX document.")

    details = _infer_upload_details(path, extracted, details, display_filename)

    doc_id = file_hash[:20]
    source_name = display_filename or path.name
    splitter = RecursiveCharacterTextSplitter(chunk_size=550, chunk_overlap=60, add_start_index=True)
    documents: list[Document] = []
    ids: list[str] = []
    for text, locator in extracted:
        if not text.strip():
            continue
        page_doc = Document(page_content=text, metadata={"locator": locator})
        chunks = splitter.split_documents([page_doc])
        for chunk_no, chunk in enumerate(chunks):
            chunk.metadata.update({
                "doc_id": doc_id,
                "source": source_name,
                "brand": details["brand"].strip(),
                "model": details["model"].strip(),
                "model_year": details["model_year"].strip(),
                "brochure_edition": details.get("brochure_edition", "").strip() or "Not stated",
                "market": details.get("market", "").strip() or "Not stated",
                "variant": details.get("variant", "").strip() or "Not specified",
                "body_type": details.get("body_type", "").strip() or "Not specified",
                "fuel_type": details.get("fuel_type", "").strip() or "Not specified",
                "active_in_india": details.get("active_in_india", "unknown"),
                "official_source_url": official_url.strip(),
            })
            documents.append(chunk)
            ids.append(f"{doc_id}-{locator.replace(' ', '-')}-{chunk_no}")

    if not documents:
        raise ValueError("No searchable text was found. This may be a scanned document; OCR is not enabled yet.")

    resolved_path = path.resolve()
    try:
        stored_path = str(resolved_path.relative_to(ROOT))
    except ValueError:
        # Keep explicitly configured external upload directories usable.
        stored_path = str(resolved_path)
    record = {
        "doc_id": doc_id,
        "sha256": file_hash,
        "filename": source_name,
        "brand": details["brand"].strip(),
        "model": details["model"].strip(),
        "model_year": details["model_year"].strip(),
        "brochure_edition": details.get("brochure_edition", "").strip() or "Not stated",
        "market": details.get("market", "").strip() or "Not stated",
        "variant": details.get("variant", "").strip() or "Not specified",
        "body_type": details.get("body_type", "").strip() or "Not specified",
        "fuel_type": details.get("fuel_type", "").strip() or "Not specified",
        "active_in_india": details.get("active_in_india", "unknown"),
        "official_source_url": official_url.strip(),
        "chunks": len(documents),
        "indexed_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="minutes"),
        "file_path": stored_path,
        "file_type": suffix[1:],
    }
    with _ingestion_lock:
        manifest = _manifest()
        existing = next((d for d in manifest["documents"] if d.get("sha256") == file_hash), None)
        if existing:
            return {**existing, "already_indexed": True}
        store = _store_instance()
        try:
            store.add_documents(documents, ids=ids)
            manifest["documents"].append(record)
            _save_manifest(manifest)
        except Exception:
            # Keep Chroma and the manifest in sync if adding passages or saving
            # their catalogue record fails part-way through.
            try:
                store.delete(ids=ids)
            except Exception:
                pass
            raise
    return record


def list_documents() -> list[dict[str, Any]]:
    return _manifest().get("documents", [])


def is_builtin_document(record: dict[str, Any]) -> bool:
    """Return whether a catalogue item is part of the supplied corpus, not a live upload."""
    stored_path = str(record.get("file_path", "")).strip()
    if not stored_path:
        return False
    path = Path(stored_path)
    resolved = path.resolve() if path.is_absolute() else (ROOT / path).resolve()
    upload_root = UPLOAD_DIR.resolve()
    try:
        resolved.relative_to(upload_root)
        return False
    except ValueError:
        return True


def search_passages(query: str, limit: int = 10) -> list[dict[str, str]]:
    """Search indexed brochure text and return evidence with source locators."""
    query = query.strip()
    catalog = list_documents()
    if not query or not catalog:
        return []

    found = _store_instance().max_marginal_relevance_search(
        query, k=limit, fetch_k=max(limit * 4, 30)
    )
    file_types = {d.get("doc_id"): d.get("file_type", "") for d in catalog}
    results = []
    for doc in found:
        metadata = doc.metadata
        results.append({
            "doc_id": metadata.get("doc_id", ""),
            "filename": metadata.get("source", "Uploaded document"),
            "brand": metadata.get("brand", ""),
            "model": metadata.get("model", ""),
            "year": metadata.get("model_year", ""),
            "brochure_edition": metadata.get("brochure_edition", "Not stated"),
            "market": metadata.get("market", "Not stated"),
            "variant": metadata.get("variant", ""),
            "locator": metadata.get("locator", ""),
            "active_in_india": metadata.get("active_in_india", "unknown"),
            "file_type": file_types.get(metadata.get("doc_id", ""), ""),
            # Extracted PDF layout can include large whitespace/newline runs;
            # keep search previews compact so one odd page cannot stretch the UI.
            "excerpt": " ".join(doc.page_content.split())[:360],
        })
    return results


def _phrase_pattern(value: str) -> str:
    """Match a catalogue phrase across spaces, hyphens, and similar punctuation."""
    parts = [re.escape(part) for part in re.split(r"[\W_]+", value.casefold()) if part]
    return r"(?<![\w])" + r"[\W_]+".join(parts) + r"(?![\w])"


_AUTO_QUERY_TERMS = {
    "boot", "space", "capacity", "volume", "length", "width", "height",
    "wheelbase", "ground", "clearance", "mileage", "range", "battery",
    "engine", "power", "torque", "safety", "airbag", "price",
    "variant", "features", "feature", "diesel", "petrol", "hybrid", "electric",
    "automatic", "manual", "sunroof", "seats", "seating", "dimensions",
    "compare", "comparison", "versus", "difference", "between",
}


def _correct_query_spelling(question: str) -> str:
    """Correct clear, one-edit typos in vehicle names and common query terms.

    Corrections are deliberately limited to terms present in the indexed
    catalogue or a small automotive vocabulary. This helps retrieval with
    misspellings without letting a language model invent a different vehicle.
    """
    catalog = list_documents()
    model_tokens = {
        token.casefold()
        for record in catalog
        for token in re.findall(r"[a-zA-Z0-9]+", record.get("model", ""))
        if len(token) >= 4
    }
    brand_tokens = {
        token.casefold()
        for record in catalog
        for token in re.findall(r"[a-zA-Z0-9]+", record.get("brand", ""))
        if len(token) >= 4
    }
    vocabulary = model_tokens | brand_tokens | _AUTO_QUERY_TERMS
    # Normalize common typos only when they are a clear near-match. Keep the
    # original punctuation and spacing so the user's question remains intact.
    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        folded = word.casefold()
        if folded == "bot":
            return "Boot" if word[:1].isupper() else "boot"
        if len(folded) < 4 or folded in vocabulary:
            return word
        matches = get_close_matches(folded, vocabulary, n=1, cutoff=0.78)
        if not matches:
            return word
        candidate = matches[0]
        # Require a single-character edit for catalogue model-name corrections;
        # otherwise a discontinued/unindexed model could be mistaken for one
        # that happens to be present.
        if candidate in model_tokens or candidate in brand_tokens:
            from difflib import SequenceMatcher
            if SequenceMatcher(None, folded, candidate).ratio() < 0.80:
                return word
        return candidate.capitalize() if word[:1].isupper() else candidate

    return re.sub(r"[A-Za-z][A-Za-z0-9-]*", replace, question)


def correct_question_spelling(question: str) -> str:
    """Return a lightly normalized version of a user's automotive question."""
    return _correct_query_spelling(question)


def _retrieval_query(question: str, brand: str = "", model: str = "") -> str:
    """Add common brochure wording so buyer terms match spec-table language."""
    additions = []
    if re.search(r"\b(boot|luggage|trunk|cargo)\b", question, re.I):
        additions.append("boot space luggage capacity cargo volume")
    if re.search(r"\b(engine|motor|power|torque|bhp|kw|cc)\b", question, re.I):
        additions.append("engine motor displacement power output torque bhp kW cc")
    if re.search(r"\b(ground clearance|clearance)\b", question, re.I):
        additions.append("ground clearance unladen laden")
    if re.search(r"\b(mileage|fuel economy|efficiency|range)\b", question, re.I):
        additions.append("fuel efficiency mileage ARAI range driving range")
    if re.search(r"\b(safety|airbag|crash)\b", question, re.I):
        additions.append("safety features airbags crash protection")
    return " ".join(part for part in [question, brand, model, *additions] if part)


def _resolve_entities(question: str, records: list[dict[str, Any]] | None = None) -> list[dict[str, str]] | None:
    """Resolve explicit model names to a brand and optional year.

    Return None for an ambiguous model name shared by brands, and [] when the
    question does not explicitly name a model in the indexed catalogue.
    """
    q = question.casefold()
    records = records if records is not None else list_documents()
    names = sorted({d["model"] for d in records if d.get("model")}, key=len, reverse=True)
    spans: list[tuple[int, int, str]] = []
    for name in names:
        pattern = re.compile(_phrase_pattern(name))
        for match in pattern.finditer(q):
            if not any(match.start() < end and match.end() > start for start, end, _ in spans):
                spans.append((match.start(), match.end(), name))

    entities = []
    mentioned_brands = {d.get("brand", "") for d in records if d.get("brand") and re.search(_phrase_pattern(d["brand"]), q)}
    for start, _end, model in sorted(spans):
        candidates = [d for d in records if d.get("model", "").casefold() == model.casefold()]
        brands = {d.get("brand", "") for d in candidates}
        matching_brands = brands.intersection(mentioned_brands)
        if len(matching_brands) == 1:
            brand = next(iter(matching_brands))
        elif len(matching_brands) > 1:
            # For same-named models, bind each occurrence to the nearest brand
            # written immediately before it (e.g. "Honda City vs Hyundai City").
            prior = []
            for candidate in matching_brands:
                starts = [m.start() for m in re.finditer(_phrase_pattern(candidate), q) if m.start() < start]
                if starts:
                    prior.append((start - max(starts), candidate))
            prior.sort()
            if prior and prior[0][0] <= 60 and (len(prior) == 1 or prior[0][0] < prior[1][0]):
                brand = prior[0][1]
            else:
                return None
        elif len(brands) == 1:
            brand = next(iter(brands))
        else:
            return None

        entity_records = [d for d in candidates if d.get("brand") == brand]
        requested_years = [d.get("model_year", "") for d in entity_records if d.get("model_year") and re.search(r"(?<!\d)" + re.escape(d["model_year"]) + r"(?!\d)", q)]
        any_year = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", q)
        edition_query = bool(re.search(r"\b(brochure|edition|updated|update|as of|dated)\b", q))
        matching_edition = edition_query and any(
            year_token in d.get("brochure_edition", "")
            for d in entity_records
            for year_token in any_year
        )
        if any_year and not requested_years and not matching_edition:
            return []
        year = requested_years[0] if requested_years else ""
        entity = {"brand": brand, "model": model, "year": year}
        if entity not in entities:
            entities.append(entity)
    return entities


def _compares_attributes_of_one_vehicle(question: str) -> bool:
    """Allow a user to compare multiple specs within one selected car."""
    categories = (
        r"\b(engine|motor|powertrain|power|torque|bhp|performance)\b",
        r"\b(safety|airbags?|crash|brakes?|adas)\b",
        r"\b(features?|equipment|technology|infotainment)\b",
        r"\b(dimensions?|length|width|height|wheelbase|ground clearance|boot|luggage)\b",
        r"\b(fuel|mileage|efficiency|range|battery|charging)\b",
        r"\b(price|cost|emi|maintenance|ownership)\b",
        r"\b(interior|comfort|seating|capacity|space)\b",
    )
    matched = sum(bool(re.search(pattern, question, re.I)) for pattern in categories)
    same_model_variants = bool(re.search(r"\b(variants?|trims?|base model|top model|entry-level|top-end)\b", question, re.I))
    return matched >= 2 or same_model_variants


def retrieve(question: str, document_ids: list[str] | None = None, built_in_only: bool = False) -> tuple[list[Document], list[dict[str, str]]]:
    docs = list_documents()
    if built_in_only:
        docs = [record for record in docs if is_builtin_document(record)]
    if not docs:
        return [], []
    store = _store_instance()
    search_question = _correct_query_spelling(question)
    selected_ids = {str(doc_id) for doc_id in (document_ids or []) if doc_id}
    selected_records = [d for d in docs if d.get("doc_id") in selected_ids]
    if selected_ids and not selected_records:
        return [], []

    if selected_ids:
        asks_for_all_selected = (
            bool(re.search(r"\b(all|both|these|selected|attached)\b", search_question, re.I))
            and bool(re.search(r"\b(cars?|vehicles?|models?|brochures?)\b", search_question, re.I))
        )
        requested_entities = [] if asks_for_all_selected else _resolve_entities(search_question, docs)
        if requested_entities is None:
            return [], []
        if requested_entities:
            groups = []
            for entity in requested_entities:
                matching = [d for d in selected_records if d.get("model", "").casefold() == entity["model"].casefold() and d.get("brand", "").casefold() == entity["brand"].casefold() and (not entity["year"] or d.get("model_year") == entity["year"])]
                if not matching:
                    return [], []
                groups.append({"brand": entity["brand"], "model": entity["model"], "year": entity["year"], "doc_ids": [d["doc_id"] for d in matching]})
        else:
            grouped: dict[tuple[str, str], dict[str, Any]] = {}
            for record in selected_records:
                key = (record.get("brand", ""), record.get("model", ""))
                group = grouped.setdefault(key, {"brand": key[0], "model": key[1], "year": "", "doc_ids": []})
                if record["doc_id"] not in group["doc_ids"]:
                    group["doc_ids"].append(record["doc_id"])
            groups = list(grouped.values())
        compare_intent = bool(re.search(r"\b(compare|comparison|versus|vs\.?|difference between|better)\b", search_question, re.I))
        if compare_intent and len(groups) < 2 and not _compares_attributes_of_one_vehicle(search_question):
            return [], []
        entities = groups
    else:
        entities = _resolve_entities(search_question, docs)

    # This capstone answers model-specific buyer questions. Requiring at least
    # one exact indexed model mention makes an absent model fail closed instead
    # of receiving a semantically similar passage about some other car.
    if entities is None or not entities:
        return [], []
    compare_intent = bool(re.search(r"\b(compare|comparison|versus|vs\.?|difference between|better)\b", search_question, re.I))
    single_vehicle_comparison = len(entities) == 1 and _compares_attributes_of_one_vehicle(search_question)
    if compare_intent and len(entities) < 2 and not single_vehicle_comparison:
        return [], []

    # Per-model retrieval prevents a single car from taking every result slot
    # in a head-to-head comparison. MMR diversifies within each model's pool.
    found: list[Document] = []
    if len(entities) >= 2:
        for entity in entities[:3]:
            where = {"$and": [{"model": {"$eq": entity["model"]}}, {"brand": {"$eq": entity["brand"]}}]}
            if entity["year"]:
                where["$and"].append({"model_year": {"$eq": entity["year"]}})
            query = _retrieval_query(search_question, entity["brand"], entity["model"])
            selected_group = bool(entity.get("doc_ids"))
            matching = store.max_marginal_relevance_search(
                query, k=4, fetch_k=10, lambda_mult=0.65, filter=where
            )
            if selected_group and not matching:
                matching = store.similarity_search(query, k=4, filter=where)
            found.extend(matching)
    elif len(entities) == 1:
        entity = entities[0]
        where = {"$and": [{"model": {"$eq": entity["model"]}}, {"brand": {"$eq": entity["brand"]}}]}
        if entity["year"]:
            where["$and"].append({"model_year": {"$eq": entity["year"]}})
        query = _retrieval_query(search_question, entity["brand"], entity["model"])
        selected_group = bool(entity.get("doc_ids"))
        found = store.max_marginal_relevance_search(
            query, k=6, fetch_k=12, lambda_mult=0.65, filter=where
        )
        if selected_group and not found:
            found = store.similarity_search(query, k=6, filter=where)

    dedup: dict[tuple[str, str, str], Document] = {}
    for doc in found:
        key = (doc.metadata.get("doc_id", ""), doc.metadata.get("locator", ""), doc.page_content)
        dedup[key] = doc
    results = list(dedup.values())
    sources: list[dict[str, str]] = []
    seen = set()
    for doc in results:
        key = (doc.metadata.get("doc_id"), doc.metadata.get("locator"))
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "filename": doc.metadata.get("source", "Uploaded document"),
            "locator": doc.metadata.get("locator", ""),
            "brand": doc.metadata.get("brand", ""),
            "model": doc.metadata.get("model", ""),
            "year": doc.metadata.get("model_year", ""),
            "variant": doc.metadata.get("variant", ""),
            "market": doc.metadata.get("market", "Not stated"),
            "official_source_url": doc.metadata.get("official_source_url", ""),
            "doc_id": doc.metadata.get("doc_id", ""),
            "active_in_india": doc.metadata.get("active_in_india", "unknown"),
            "file_type": next((d.get("file_type", "") for d in docs if d.get("doc_id") == doc.metadata.get("doc_id")), ""),
        })
    return results, sources


def context_for(docs: list[Document]) -> str:
    sections = []
    for doc in docs:
        m = doc.metadata
        # Keep only metadata needed to prevent model/year/variant/market mixing.
        # Source filename, page locator and current-status tags are displayed by
        # the UI and need not be repeated in the generation prompt.
        scope_parts = [f"{m.get('brand', '')} {m.get('model', '')}".strip()]
        for label, key in (
            ("year", "model_year"), ("variant", "variant"), ("fuel", "fuel_type"),
            ("market", "market"), ("edition", "brochure_edition"),
        ):
            value = str(m.get(key, "")).strip()
            if value and value.casefold() not in {"not stated", "not specified", "unknown", "n/a"}:
                scope_parts.append(f"{label} {value}")
        scope = " | ".join(part for part in scope_parts if part)
        sections.append(f"[{scope}]\n{doc.page_content}")
    return "\n\n---\n\n".join(sections)

