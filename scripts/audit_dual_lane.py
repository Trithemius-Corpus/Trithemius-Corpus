"""Offline audit of the cached v2 dual-context translation lane.

Reads the already-produced GPT-5.5 translations (over the Qwen3-VL "Trithemius"
LoRA OCR) and runs the strengthened v3 output guards against them. This is a
diagnostic: it measures how many cached chunks the guards flag and of what
type, *before* spending API budget on a guarded re-run. It never modifies the
cached translations.

Inputs (per work, in the working corpus at TRITHEMIUS_WORKING/data/corpus):
  <work>/translations/_reocr/qwen3vl-4b-trithemius-q6/full.txt   (LoRA OCR)
  <work>/translations/qwen3vl-trithemius-q6-dual-gpt55/full/runs.jsonl
  <work>/translations/qwen3vl-trithemius-q6-dual-gpt55/full/full_chunk_NNNN.md

Output: a per-chunk JSONL report plus a printed summary table. Use --control to
run the same audit against a control set (faithful works) to measure the
guards' false-positive rate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from v3_output_guards import validate_translation_output  # noqa: E402

WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"
LANE = "qwen3vl-trithemius-q6-dual-gpt55"
OCR_ENGINE = "qwen3vl-4b-trithemius-q6"

# The six works that dragged the v2 lane's mean down (faith < 3.0 or C/F tier).
FAILING_WORKS = [
    "prdl-70280_e-rara_de-scriptoribus-ecclesiasticis-johannes-trithemius",
    "prdl-70289_opera-historica-part",
    "prdl-70290_opera-historica-part-chronicon-hirsaugiense-sponheimense",
    "prdl-24360_compendium-breviarium-primi-voluminis-annalium-historiarum-origine-regum",
    "prdl-24393_sermones-et-exhortationes-ad-monachos-joa",
    "prdl-24394_sermones-et-exhortationes-ad-monachos-joa",
]

# Six S-tier control works (the lane's best results). The guards should NOT
# flag these; any flag here is a false positive to tune out.
CONTROL_WORKS = [
    "prdl-24381_octo-quaestionum-maximilianum-caesarem",
    "prdl-24382_octo-quaestionum-maximilianum-caesarem",
    "prdl-32287_e-rara_trithemius-sui-ipsius-vindex-sive",
    "prdl-70286_octo-quaestionum-maximilianum-caesarem",
    "prdl-24362_de-laude-scriptorum-manualium",
    "prdl-32286_octo-quaestionum-maximilianum-caesarem",
]

PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)


def page_map(full_text: str) -> dict[int, str]:
    matches = list(PAGE_RE.finditer(full_text))
    out: dict[int, str] = {}
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        out[int(match.group(1))] = full_text[start:end].strip()
    return out


def collect_pages(mapping: dict[int, str], pages: list[int]) -> str:
    parts = []
    for page in pages:
        if page in mapping:
            parts.append("--- Page %03d ---\n%s" % (page, mapping[page]))
    return "\n\n".join(parts).strip()


def audit_work(work_id: str, out_dir: Path) -> dict[str, Any]:
    work_dir = CORPUS / work_id
    lane_dir = work_dir / "translations" / LANE / "full"
    ocr_full = work_dir / "translations" / "_reocr" / OCR_ENGINE / "full.txt"
    runs_jsonl = lane_dir / "runs.jsonl"

    if not ocr_full.exists():
        return {"work": work_id, "error": "missing OCR full.txt", "chunks": []}
    if not runs_jsonl.exists():
        return {"work": work_id, "error": "missing runs.jsonl", "chunks": []}

    pm = page_map(ocr_full.read_text(encoding="utf-8", errors="replace"))

    chunk_reports: list[dict[str, Any]] = []
    for line in runs_jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        index = rec["chunk"]
        pages = rec.get("pages", [])
        chunk_file = lane_dir / ("full_chunk_%04d.md" % index)
        english = ""
        if chunk_file.exists():
            english = chunk_file.read_text(encoding="utf-8", errors="replace")

        primary = collect_pages(pm, pages)
        guard = validate_translation_output(
            output_text=english,
            expected_pages=pages,
            source_text=primary,
            require_source_anchor=True,
        )
        chunk_reports.append({
            "chunk": index,
            "pages": pages,
            "english_chars": len(english),
            "blocking_issues": guard["blocking_issues"],
            "anchor_hits": len(guard["source_anchor_hits"]),
            "anchor_misses": len(guard["source_anchor_misses"]),
            "overlap_ratio": round(guard["source_content_overlap"], 3),
            "overlap_words": guard["source_overlap_words"],
        })

    return {"work": work_id, "chunks": chunk_reports}


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    chunks = result.get("chunks", [])
    if not chunks:
        return {"work": result["work"], "error": result.get("error", "no chunks")}
    flagged = [c for c in chunks if c["blocking_issues"]]
    by_issue: Counter = Counter()
    for c in flagged:
        for issue in set(c["blocking_issues"]):
            by_issue[issue] += 1
    overlaps = [c["overlap_ratio"] for c in chunks if c["overlap_words"] >= 8]
    return {
        "work": result["work"],
        "total_chunks": len(chunks),
        "flagged_chunks": len(flagged),
        "flagged_pct": round(len(flagged) / len(chunks) * 100, 1) if chunks else 0,
        "by_issue": dict(by_issue),
        "median_overlap": round(sorted(overlaps)[len(overlaps) // 2], 3) if overlaps else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--control", action="store_true",
                    help="Audit the S-tier control set instead of the failing works.")
    ap.add_argument("--both", action="store_true",
                    help="Audit both the failing and control sets.")
    ap.add_argument("--out", type=Path, default=ROOT / ".cache" / "dual_lane_audit",
                    help="Output directory for per-chunk JSONL reports.")
    args = ap.parse_args()

    sets = []
    if args.both:
        sets = [("FAILING", FAILING_WORKS), ("CONTROL", CONTROL_WORKS)]
    elif args.control:
        sets = [("CONTROL", CONTROL_WORKS)]
    else:
        sets = [("FAILING", FAILING_WORKS)]

    args.out.mkdir(parents=True, exist_ok=True)
    for label, works in sets:
        print("=" * 72)
        print("%s SET (%d works)" % (label, len(works)))
        print("=" * 72)
        print("%-46s %6s %6s %6s  %s" % (
            "work", "chunks", "flagd", "flag%", "by issue"))
        print("-" * 72)
        all_flagged = 0
        all_total = 0
        for work in works:
            result = audit_work(work, args.out)
            summary = summarize(result)
            if "error" in summary:
                print("%-46s  ERROR: %s" % (work[:46], summary["error"]))
                continue
            slug = work.split("_", 1)[0]
            safe = "%s.jsonl" % slug
            (args.out / safe).write_text(
                "\n".join(json.dumps(c, ensure_ascii=False) for c in result["chunks"]) + "\n",
                encoding="utf-8",
            )
            issue_str = ", ".join("%s=%d" % (k, v) for k, v in sorted(summary["by_issue"].items())) or "-"
            print("%-46s %6d %6d %5.1f%%  %s" % (
                work[:46], summary["total_chunks"], summary["flagged_chunks"],
                summary["flagged_pct"], issue_str))
            all_flagged += summary["flagged_chunks"]
            all_total += summary["total_chunks"]
        print("-" * 72)
        pct = all_flagged / all_total * 100 if all_total else 0
        print("%-46s %6d %6d %5.1f%%  (%s set total)" % ("TOTAL", all_total, all_flagged, pct, label))
        print()
    print("Per-chunk reports written to: %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
