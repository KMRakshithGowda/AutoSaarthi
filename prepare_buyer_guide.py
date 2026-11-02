"""Create vehicle-scoped searchable entries from AutoSaarthi project guides."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
GUIDE = DATA / "sources" / "BuyerGuide" / "AutoSaarthi_40_Cars_Indian_Buyer_Guide.docx"
REVIEWS = DATA / "sources" / "BuyerGuide" / "AutoSaarthi_40_Cars_Comprehensive_Reviews_Dataset.docx"
CATALOG = DATA / "catalog.csv"
SCOPE = DATA / "project_scope.json"
MAPPING = DATA / "source_mapping.json"

# Both Word files use matching numbered sections. Exclude duplicate and inactive
# entries, and do not misattribute the source's erroneous "Tata Swift" heading.
TARGETS = {
    1: [("Maruti Suzuki", "WagonR", "")], 2: [("Maruti Suzuki", "Baleno", "")],
    4: [("Honda", "Amaze", "")], 5: [("Honda", "City", "")],
    6: [("Hyundai", "Verna", "")], 7: [("Volkswagen", "Virtus", "")],
    8: [("Maruti Suzuki", "Brezza", "")], 9: [("Tata", "Nexon", "")],
    10: [("Hyundai", "Venue", "")], 12: [("Mahindra", "XUV 3X0", "")],
    13: [("Renault", "Kwid", "")], 14: [("Hyundai", "Bayon", "")],
    15: [("Hyundai", "Creta", "")], 16: [("Kia", "Seltos", "")],
    17: [("Toyota", "Urban Cruiser Hyryder", "This section groups Hyryder with Maruti Grand Vitara; the guide does not separate figures by model or variant.")],
    18: [("Tata", "Curvv", "This section groups Curvv and Curvv EV without assigning figures to a specific powertrain."), ("Tata", "Curvv EV", "This section groups Curvv and Curvv EV without assigning figures to a specific powertrain.")],
    19: [("Volkswagen", "Taigun", "")], 20: [("Renault", "Duster", "")],
    21: [("MG", "Hector", "")], 22: [("Mahindra", "Thar Roxx", "")],
    23: [("Maruti Suzuki", "Ertiga", "")], 24: [("Toyota", "Rumion", "")],
    25: [("Toyota", "Innova Crysta", "")],
    26: [("Toyota", "Innova Hycross", "This section groups Hycross with Invicto without separating figures; heading attribution may be inaccurate.")],
    27: [("Kia", "Carens", "")], 28: [("Mahindra", "Scorpio-N", "")],
    29: [("Tata", "Safari", "")], 30: [("Hyundai", "Alcazar", "")],
    31: [("Toyota", "Legender", "")], 32: [("Tata", "Punch", "")],
    34: [("Tata", "Harrier", "")], 35: [("Toyota", "Hilux", "")],
    36: [("Maruti Suzuki", "Swift", "")], 37: [("Tata", "Sierra", "")],
    38: [("Mahindra", "Bolero", "")], 40: [("Hyundai", "i20", "")],
}


def parse_sections(path: Path) -> dict[int, tuple[str, list[str]]]:
    if not path.is_file():
        raise SystemExit(f"Missing source document: {path}")
    sections: dict[int, tuple[str, list[str]]] = {}
    current = None
    for para in Document(str(path)).paragraphs:
        text = " ".join(para.text.split())
        if not text:
            continue
        match = re.match(r"^(\d+)\.\s+(.+)$", text)
        if match:
            current = int(match.group(1))
            sections[current] = (match.group(2), [])
        elif current is not None:
            sections[current][1].append(text)
    return sections


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    inputs = [
        (parse_sections(GUIDE), "buyer_guide", GUIDE, "vehicle_sections", "Buyer Guide", "Project-supplied buyer-guide figures; not independently verified."),
        (parse_sections(REVIEWS), "expert_user_reviews", REVIEWS, "review_sections", "Comprehensive Expert and User Reviews", "Project-supplied review summary; scores and safety claims are not independently verified."),
    ]
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    active = {(v["brand"], v["model"]): v for v in scope["active_vehicles"]}
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    indexed_files = {
        str(item.get("file_path", "")).replace("\\", "/").replace("Data/sources/", "")
        for item in manifest.get("documents", [])
    }
    generated = []
    output_types = {item[1] for item in inputs}

    for sections, source_type, original, subdir, label, caution in inputs:
        for number, targets in TARGETS.items():
            if number not in sections:
                raise SystemExit(f"Missing section {number} in {original.name}; no catalogue writes performed.")
            heading, body = sections[number]
            for brand, model, note in targets:
                if (brand, model) not in active:
                    raise SystemExit(f"Target is not in active scope: {brand} {model}")
                slug = re.sub(r"[^A-Za-z0-9]+", "_", f"{brand}_{model}").strip("_")
                relative = Path("BuyerGuide") / subdir / f"{slug}.md"
                destination = DATA / "sources" / relative
                content = [
                    f"Source: {original.name}, section {number} ({heading}); project-supplied, unverified.",
                ]
                if note:
                    content.append(f"Mapping note: {note}")
                # Keep the provenance line and all facts in one paragraph so
                # the retriever can return ratings/specs with their context.
                content.extend(body)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text("\n".join(content), encoding="utf-8")
                generated.append({
                    "brand": brand, "model": model, "model_year": "Not stated",
                    "brochure_edition": "", "market": "India", "variant": "",
                    "body_type": "", "fuel_type": "", "active_in_india": "unknown",
                    "brochure_filename": relative.as_posix(), "official_source_url": "",
                    "source_type": source_type,
                })

    with CATALOG.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        catalog_rows = [row for row in reader if row.get("source_type") not in output_types]
    with CATALOG.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(catalog_rows + generated)

    for vehicle in scope["active_vehicles"]:
        vehicle["source_files"] = [s for s in vehicle.get("source_files", []) if s.get("source_type") not in output_types]
    for row in generated:
        active[(row["brand"], row["model"])]["source_files"].append({
            "filename": row["brochure_filename"], "source_type": row["source_type"],
            "status": "indexed" if row["brochure_filename"] in indexed_files else "ready_to_index",
        })
    atomic_json(SCOPE, scope)

    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    mapped = {(v["brand"], v["model"]): v for v in mapping["vehicles"]}
    for vehicle in mapping["vehicles"]:
        vehicle["sources"] = [s for s in vehicle.get("sources", []) if s.get("source_type") not in output_types]
    for row in generated:
        mapped[(row["brand"], row["model"])]["sources"].append({
            "filename": row["brochure_filename"], "source_type": row["source_type"],
            "status": "indexed" if row["brochure_filename"] in indexed_files else "ready_to_index",
        })
    atomic_json(MAPPING, mapping)
    for source_type in sorted(output_types):
        print(f"{source_type}: {sum(r['source_type'] == source_type for r in generated)} active vehicle entries")
    print("Duplicate, ambiguous, and out-of-scope sections remain only in the original DOCX files.")


if __name__ == "__main__":
    main()
