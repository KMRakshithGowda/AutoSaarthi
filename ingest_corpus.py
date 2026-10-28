"""Batch-index the user's manually supplied brochures listed in Data/catalog.csv."""
import csv
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from src.rag import DATA_DIR, ingest_file

CATALOG = DATA_DIR / "catalog.csv"
SOURCE_DIR = Path(os.getenv("SOURCE_DIR", str(DATA_DIR / "sources")))
if not SOURCE_DIR.is_absolute():
    SOURCE_DIR = DATA_DIR / SOURCE_DIR
REQUIRED = {"brand", "model", "model_year", "brochure_filename"}


def main():
    if not CATALOG.exists():
        raise SystemExit(f"Missing catalogue: {CATALOG}")
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    with CATALOG.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise SystemExit("catalog.csv needs columns: " + ", ".join(sorted(REQUIRED)))
        rows = list(reader)

    indexed = skipped = 0
    for row_no, row in enumerate(rows, 2):
        filename = (row.get("brochure_filename") or "").strip()
        if not filename:
            continue
        source = (SOURCE_DIR / filename).resolve()
        if SOURCE_DIR.resolve() not in source.parents:
            print(f"Row {row_no}: skipped unsafe filename")
            skipped += 1
            continue
        if not source.is_file():
            print(f"Row {row_no}: missing file {filename}")
            skipped += 1
            continue
        details = {k: (row.get(k) or "").strip() for k in ("brand", "model", "model_year", "brochure_edition", "market", "variant", "body_type", "fuel_type")}
        if not all(details[k] for k in ("brand", "model", "model_year")):
            print(f"Row {row_no}: missing brand, model, or model_year")
            skipped += 1
            continue
        coverage_status = (row.get("active_in_india") or "").strip().lower()
        if coverage_status in {"yes", "true", "1", "active", "current"}:
            details["active_in_india"] = "yes"
        elif coverage_status in {"archive", "no", "false", "discontinued"}:
            details["active_in_india"] = "archive"
        else:
            details["active_in_india"] = "unknown"
        try:
            record = ingest_file(source, details, (row.get("official_source_url") or "").strip())
            print(f"Indexed {record['brand']} {record['model']} {record['model_year']}: {record['chunks']} passages")
            indexed += 1
        except ValueError as exc:
            print(f"Row {row_no}: {exc}")
            skipped += 1
    print(f"Finished: {indexed} document(s) indexed; {skipped} row(s) skipped.")


if __name__ == "__main__":
    main()

