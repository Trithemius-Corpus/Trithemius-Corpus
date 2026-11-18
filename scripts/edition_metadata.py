"""Shared editorial evidence for the web reader, catalogue and book exports."""
from __future__ import annotations

QA_LABELS = {
    "full-machine-audit": "Full machine audit",
    "sampled-machine-audit": "Sampled machine audit",
    "not-independently-audited": "No independent machine audit recorded",
    "historical-machine-audit": "Historical machine audit (before local corrections)",
}
STATE_LABELS = {
    "provisional-reading-text": "Provisional reading text",
    "prepared-reading-text": "Prepared reading text",
    "editorially-reviewed-reading-view": "Editorially reviewed reading view",
    "structured-diplomatic-view": "Structured diplomatic view",
    "ai-corrected-reading-text": "AI-corrected provisional reading text",
}
STRUCTURED = ("prdl-24389_", "prdl-24391_", "prdl-24395_", "prdl-70282_", "prdl-70291_", "prdl-70292_")


def editorial_record(meta: dict, track: str, reviews: dict) -> dict:
    graded = int(meta.get("chunks_graded") or 0)
    total = int(meta.get("chunks_total") or 0)
    if not 0 <= graded <= total:
        raise ValueError(f"{meta['id']}: invalid audit coverage {graded}/{total}")
    audit = "not-independently-audited"
    if graded:
        audit = "full-machine-audit" if graded == total else "sampled-machine-audit"
    state = "provisional-reading-text" if track == "earlier" else "prepared-reading-text"
    if track == "trithemius-4b" and meta["id"].startswith(STRUCTURED):
        state = "structured-diplomatic-view"
    record = {
        "id": meta["id"], "edition_track": track, "text_origin": "machine-translation",
        "human_review": "none-documented", "editorial_state": state, "automated_qa": audit,
        "automated_qa_coverage_pct": round(100 * graded / total, 1) if total else 0.0,
        "chunks_graded": graded, "chunks_total": total, "internal_triage": "C",
        "known_limitations": ["not-human-verified", "check-against-latin-before-quotation"],
        "historical_machine_grade": meta.get("tier"),
        "historical_faithfulness_score": meta.get("faithful_adj"),
    }
    review = reviews.get(f"{meta['id']}::{track}", {})
    if review.get("status") == "approved" and review.get("scope") == "reading-view":
        record.update(human_review="editorial-reading-view", editorial_state="editorially-reviewed-reading-view",
                      review_date=review.get("date"), review_note=review.get("note"))
    if meta.get("ai_corrections"):
        record.update(editorial_state="ai-corrected-reading-text", automated_qa="historical-machine-audit",
                      historical_qa_scope=audit, ai_corrections=meta["ai_corrections"])
    return record


def attribution(work: dict) -> dict:
    return work.get("attribution") or {"author": "Johannes Trithemius"}


def credit(work: dict) -> str:
    record = attribution(work)
    if record.get("transmitted_by"):
        return f"{record['author']}, transmitted by {record['transmitted_by']}"
    if record.get("attributed_to"):
        return f"Unidentified author, traditionally attributed to {record['attributed_to']}"
    return record["author"]
