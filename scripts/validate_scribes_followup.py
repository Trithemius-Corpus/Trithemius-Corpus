"""Replay the Scribes revision history and verify its current public readings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lxml import html

import build_translation_disagreements as b
from edition_corrections import history, recorded_ledgers, validate_history
import scan_evidence


def validate(dist: Path) -> None:
    work = b.DEFAULT_WORK
    base = b.ROOT / "data/translation_disagreements" / work
    ledgers = history(b.ROOT, work)
    validate_history(b.ROOT, work, ledgers)
    scans = scan_evidence.load(b.ROOT, work)
    changes = [edit for ledger in ledgers for edit in ledger["changes"]]
    active = b.current_resolutions(ledgers)
    for ledger in ledgers:
        assessed = scan_evidence.load(b.ROOT, work, as_of=ledger["date"])
        if any(change["item_id"] not in assessed for change in ledger["changes"]):
            raise ValueError("A correction has no scan assessment at its recorded date")
    spec = json.loads(b.read(base / "review.json"))
    before = json.loads(b.read(b.ROOT / spec["sources"]["passage_index"]["path"]))
    after = json.loads(b.read(dist / "data/passages" / f"{work}.json"))
    for name in ("passages", "annotations"):
        if [x["id"] for x in before[name]] != [x["id"] for x in after[name]]:
            raise ValueError(f"{name} IDs changed")
    for track, folder in (("earlier", "works"), ("t4b", "works-t4b")):
        edition = b.ROOT / folder / work
        metadata = json.loads(b.read(edition / "metadata.json"))["ai_corrections"]
        edits = [c for c in changes if c["track"] == track]
        if (metadata["count"] != len(edits) or metadata["human_review"] != "none_documented"
                or metadata["date"] != max(ledger["date"] for ledger in ledgers
                                           if any(c["track"] == track for c in ledger["changes"]))):
            raise ValueError(f"{track}: edition metadata differs from the revision history")
        errata = b.read(edition / "ERRATA.md")
        for edit in edits:
            if any(edit[key] not in errata for key in ("item_id", "before", "after")):
                raise ValueError(f"{track}: missing erratum for {edit['item_id']}")
        suffix = "" if track == "earlier" else "-trithemius-4b"
        doc = html.fromstring(b.read(dist / "works" / f"{work}{suffix}.html"))
        body = doc.get_element_by_id("study-reader" if track == "earlier" else "reading-text")
        text = b.flat(body.text_content())
        for item_id, resolution in active.items():
            for change in resolution["changes"]:
                if change["track"] == track and b.flat(change["after"]) not in text:
                    raise ValueError(f"{track}: current reading missing for {item_id}")
        for edit in edits:
            if b.flat(edit["before"]) in text:
                raise ValueError(f"{track}: superseded reading present for {edit['item_id']}")

    seeds = json.loads(b.read(base / "benchmark-seed.json"))
    active_ids = [f["id"] for f in seeds["fixtures"]]
    held = {f["id"] for f in seeds["withheld"]}
    original_ids = set(recorded_ledgers(b.ROOT, work, "scans")[0]["items"])
    expected_held = {k for k, v in scans.items() if v.get("benchmark_status") == "withheld_pending_human_adjudication"}
    if (seeds["human_verified"] is not False or held != expected_held
            or len(set(active_ids)) != len(active_ids) or set(active_ids) != original_ids - held):
        raise ValueError("Benchmark fixtures and withheld readings are inconsistent")
    for fixture in seeds["fixtures"]:
        key = fixture["id"]
        if (fixture["latin"] != scans[key]["normalized_latin"] or fixture["source_image"] != scans[key]["image"]
                or set(fixture["accepted_local_english"]) != {c["after"] for c in active[key]["changes"]}):
            raise ValueError(f"Benchmark seed differs from the current evidence: {key}")
    print(f"Scribes correction checks passed for {len(changes)} edits in {len(ledgers)} dated batches, "
          f"{len(after['passages'])} passages and {len(after['annotations'])} annotation IDs.")
    print(f"{len(active_ids)} provisional benchmark seeds and {len(held)} withheld pending human adjudication.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=b.ROOT / "site/dist")
    validate(parser.parse_args().dist)


if __name__ == "__main__":
    main()
