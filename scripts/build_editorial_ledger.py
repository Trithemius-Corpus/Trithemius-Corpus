"""Build the public editorial-status ledger for every translated edition."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "editorial_status.json"
REVIEWS = ROOT / "data" / "editorial_reviews.json"


def qa_status(meta: dict) -> tuple[str, float]:
    graded = int(meta.get("chunks_graded") or 0)
    total = int(meta.get("chunks_total") or 0)
    coverage = graded / total * 100 if total else float(meta.get("coverage_pct") or 0)
    if graded and coverage >= 95:
        return "full-machine-audit", round(coverage, 1)
    if graded:
        return "sampled-machine-audit", round(coverage, 1)
    return "not-independently-audited", 0.0


def record(meta: dict, track: str, editorial_state: str) -> dict:
    qa, coverage = qa_status(meta)
    return {
        "id": meta["id"],
        "edition_track": track,
        "text_origin": "machine-translation",
        "human_review": "none-documented",
        "editorial_state": editorial_state,
        "automated_qa": qa,
        "automated_qa_coverage_pct": coverage,
        "internal_triage": "C",
        "known_limitations": [
            "not-human-verified",
            "check-against-latin-before-quotation",
        ],
        "historical_machine_grade": meta.get("tier"),
        "historical_faithfulness_score": meta.get("faithful_adj"),
    }


def main() -> int:
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8")).get("reviews", {}) if REVIEWS.exists() else {}
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    records = [
        record(work, "earlier", "provisional-reading-text")
        for work in manifest.get("works", []) if not work.get("skip")
    ]

    for meta_path in sorted((ROOT / "works-t4b").glob("*/metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        # All T4B pages have received display-level editorial cleanup. Six
        # structurally sensitive cipher/sigil works intentionally retain their
        # segment divisions and are labeled accordingly.
        specialized = any(meta["id"].startswith(prefix) for prefix in (
            "prdl-24389_", "prdl-24391_", "prdl-24395_",
            "prdl-70282_", "prdl-70291_", "prdl-70292_",
        ))
        state = "structured-diplomatic-view" if specialized else "prepared-reading-text"
        edition = record(meta, "trithemius-4b", state)
        review = reviews.get(f"{meta['id']}::trithemius-4b", {})
        if review.get("status") == "approved" and review.get("scope") == "reading-view":
            edition["human_review"] = "editorial-reading-view"
            edition["editorial_state"] = "editorially-reviewed-reading-view"
            edition["review_date"] = review.get("date")
            edition["review_note"] = review.get("note")
        records.append(edition)

    payload = {
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
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} edition records to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
