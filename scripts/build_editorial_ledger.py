"""Build the public editorial-status ledger for every translated edition."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "editorial_status.json"
REVIEWS = ROOT / "data" / "editorial_reviews.json"


def payload() -> dict:
    from edition_metadata import editorial_record
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8"))["reviews"]
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    records = [editorial_record(w, "earlier", reviews) for w in manifest["works"] if not w["skip"]]
    for path in sorted((ROOT / "works-t4b").glob("*/metadata.json")):
        records.append(editorial_record(json.loads(path.read_text(encoding="utf-8")), "trithemius-4b", reviews))
    return {
        "schema_version": 1,
        "policy": {
            "public_letter_grades": False,
            "machine_translation_default_internal_triage": "C",
            "human_review_required_for_promotion": True,
            "historical_machine_grades_retained_for_provenance": True,
        },
        "counts": {
            "editions": len(records),
            "human_reviewed_complete": sum(r["human_review"] == "complete" for r in records),
            "machine_translations": sum(r["text_origin"] == "machine-translation" for r in records),
        },
        "editions": records,
    }



def summary() -> str:
    from build_site import text_group_key, load_first_english, load_manifest
    works = [w for w in load_manifest()["works"] if not w["skip"]]
    survey = load_first_english()
    group = [w for w in works if survey[w["id"]]["status"] in {"partial_prior", "none_located"}]
    return (f"Provisional English translations of {len({text_group_key(w) for w in works})} Latin texts across "
            f"{len(works)} printed witnesses in the Trithemius Corpus. The project survey located no prior complete "
            f"published English translation for {len({text_group_key(w) for w in group})} texts ({len(group)} witnesses). "
            "Edition records distinguish machine translation, editorial preparation, human review and automated "
            "audit coverage. Earlier machine scores are historical. Latin transcription, source scans, and "
            "documented corrections support verification of individual passages.")


def distribution_files() -> dict:
    import re
    description = summary()
    title = "Trithemius Corpus: machine-assisted English translations of Latin texts by or associated with Johannes Trithemius"
    citation = ROOT / "CITATION.cff"
    text = re.sub(r"(?ms)^abstract: >.*?(?=^type: dataset)", "abstract: >\n  " + description + "\n", citation.read_text(encoding="utf-8"))
    text = re.sub(r"(?m)^title: .*?$", "title: " + json.dumps(title), text, count=1)
    zenodo = ROOT / ".zenodo.json"
    data = json.loads(zenodo.read_text(encoding="utf-8"))
    data["description"] = description
    data["title"] = title
    return {citation: text, zenodo: json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            OUT: json.dumps(payload(), ensure_ascii=False, indent=2) + "\n"}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, value in distribution_files().items():
        if args.check and path.read_text(encoding="utf-8") != value:
            raise ValueError(f"Stale editorial metadata in {path.name}")
        if not args.check:
            path.write_text(value, encoding="utf-8", newline="\n")
    print("Editorial status and distribution metadata are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
