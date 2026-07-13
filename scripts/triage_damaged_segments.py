#!/usr/bin/env python3
"""Stage 1 triage: find segments the translator refused as OCR-damaged, map
each to its source work + chunk + backing page scans, and emit a worklist
(damaged_segments.json) for human review before any re-OCR or re-translation.

A "refused" segment is one whose English reads as an illegibility notice, e.g.
"[Source page illegible in the scan; the page image is the authoritative
witness.]" — the existing pipeline correctly declined to translate these rather
than hallucinate through fragmented OCR. Re-OCR (not MT) is the fix.

Usage:
    python scripts/triage_damaged_segments.py
    python scripts/triage_damaged_segments.py --work prdl-24382_...
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKS = ROOT / "works"
WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"

# Phrases the existing translator used to refuse OCR-damaged segments.
REFUSE_PATTERNS = [
    r"illegible in the scan",
    r"page image is the authoritative",
    r"unreadable in the scan",
    r"too damaged to translate",
    r"scan.*illegible",
    r"illegible.*authoritative witness",
]
REFUSE_RE = re.compile("|".join(REFUSE_PATTERNS), re.I)

# Lazy import of the facsimile chunk->page mapper.
_sys_path_added = False


def _facsimile_map():
    global _sys_path_added
    if not _sys_path_added:
        sys.path.insert(0, str(ROOT / "scripts"))
        _sys_path_added = True
    import facsimile_map as fm  # noqa: E402
    return fm


def find_works() -> list[str]:
    return sorted(d.name for d in WORKS.iterdir() if (d / "english.md").exists())


def page_scans_for(work_id: str) -> set[str]:
    d = CORPUS / work_id / "pages"
    if not d.exists():
        return set()
    return {p.stem.replace("page_", "") for p in d.glob("page_*.png")}


def has_reocr(work_id: str) -> list[str]:
    """Return the list of existing _reocr engines for this work, if any."""
    base = CORPUS / work_id / "translations" / "_reocr"
    if not base.exists():
        return []
    return [d.name for d in base.iterdir() if d.is_dir() and (d / "full.txt").exists()]


def chunk_for_segment(work_id: str, refused_text: str) -> tuple[int, str] | None:
    """Find the chunk whose English contains this refused notice, and return
    (chunk_index, the surrounding latin from latin-ocr.txt). Tries to locate the
    refused text inside a chunk file; returns None if no chunk matches."""
    chunks_dir = WORKS / work_id / "chunks"
    if not chunks_dir.exists():
        return None
    # the refused notice is short; match a distinctive fragment
    frag = re.sub(r"\W+", "", refused_text)[:40].lower()
    for cf in sorted(chunks_dir.glob("full_chunk_*.md")):
        text = cf.read_text(encoding="utf-8")
        norm = re.sub(r"\W+", "", text).lower()
        if frag in norm:
            m = re.search(r"(\d+)", cf.stem)
            return (int(m.group(1)) if m else -1, text)
    return None


def triage(work_id: str, fm) -> list[dict]:
    eng_path = WORKS / work_id / "english.md"
    if not eng_path.exists():
        return []
    text = eng_path.read_text(encoding="utf-8")
    rec_pages = fm.rec_pages_for_work(work_id)
    # Build an interpolated page map: a chunk with no `--- Page ---` markers
    # sits between two marker-bearing chunks, so its pages are the span from the
    # previous chunk's last page to the next chunk's first page (inclusive).
    interp_pages = _interpolate_pages(rec_pages)

    findings = []
    seen_paras: set[str] = set()
    for m in REFUSE_RE.finditer(text):
        start = text.rfind("\n\n", 0, m.start()) + 2
        end = text.find("\n\n", m.start())
        if end == -1:
            end = len(text)
        para = text[start:end].strip()
        if para in seen_paras:
            continue  # dedup: multiple refuse-phrases in one paragraph
        seen_paras.add(para)
        line = text.count("\n", 0, m.start()) + 1
        chunk_info = chunk_for_segment(work_id, para)
        chunk_idx = chunk_info[0] if chunk_info else None
        pages = []
        if chunk_idx and chunk_idx > 0:
            pages = rec_pages.get(chunk_idx) or interp_pages.get(chunk_idx, [])
        findings.append({
            "work_id": work_id,
            "english_md_line": line,
            "chunk": chunk_idx,
            "source_pages": pages,
            "refused_english": para[:200],
        })
    return findings


def _interpolate_pages(rec_pages: dict[int, list[int]]) -> dict[int, list[int]]:
    """For chunks that have no page markers, infer their pages from neighbouring
    marker-bearing chunks (previous chunk's last page .. next chunk's first)."""
    if not rec_pages:
        return {}
    idxs = sorted(rec_pages)
    out: dict[int, list[int]] = {}
    for i in idxs:
        if rec_pages[i]:  # already known
            continue
        # walk back to the last chunk with pages
        prev_pages = next((rec_pages[j] for j in reversed(idxs) if j < i and rec_pages[j]), None)
        # walk forward to the next chunk with pages
        next_pages = next((rec_pages[j] for j in idxs if j > i and rec_pages[j]), None)
        if prev_pages and next_pages:
            lo, hi = prev_pages[-1], next_pages[0]
            if lo <= hi:
                out[i] = list(range(lo, hi + 1))
            else:
                out[i] = [lo]
        elif prev_pages:
            out[i] = [prev_pages[-1]]
        elif next_pages:
            out[i] = [next_pages[0]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", help="triage a single work")
    ap.add_argument("--out", default=str(ROOT / "damaged_segments.json"))
    args = ap.parse_args()

    fm = _facsimile_map()
    works = [args.work] if args.work else find_works()

    all_findings: list[dict] = []
    per_work_summary = []
    for wid in works:
        findings = triage(wid, fm)
        if not findings:
            continue
        scans = page_scans_for(wid)
        reocr = has_reocr(wid)
        has_scans_dir = bool(scans)
        # attach scan/reocr availability to each finding's work
        for f in findings:
            if f["source_pages"]:
                missing_pages = [str(p) for p in f["source_pages"]
                                 if str(p).zfill(3) not in scans]
                f["page_scans_present"] = len(missing_pages) == 0
                f["missing_scans"] = missing_pages
            else:
                # no page mapping at all — scans status unknown
                f["page_scans_present"] = None
                f["missing_scans"] = ["(no page mapping — full.txt/pages absent)"]
            f["reocr_engines"] = reocr
        all_findings.extend(findings)
        per_work_summary.append({
            "work_id": wid,
            "segments": len(findings),
            "pages_needed": sorted({p for f in findings for p in f["source_pages"]}),
            "has_page_scans": has_scans_dir and any(f["source_pages"] for f in findings),
            "has_reocr": reocr,
        })

    out = {
        "description": "Segments the translator refused as OCR-damaged, "
                       "mapped to source pages for re-OCR. Review before re-OCR/translation.",
        "total_segments": len(all_findings),
        "total_works": len(per_work_summary),
        "per_work": sorted(per_work_summary, key=lambda w: -w["segments"]),
        "segments": all_findings,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # human-readable summary
    print(f"\n{'='*72}")
    print(f"DAMAGED-SEGMENT TRIAGE: {len(all_findings)} segments across "
          f"{len(per_work_summary)} works")
    print(f"{'='*72}")
    print(f"{'WORK':<48} {'SEGS':>4} {'PAGES':>6} {'SCANS':>6} {'REOCR':>6}")
    print("-" * 72)
    for w in out["per_work"]:
        print(f"{w['work_id'][:47]:<48} {w['segments']:>4} "
              f"{len(w['pages_needed']):>6} "
              f"{'yes' if w['has_page_scans'] else 'NO':>6} "
              f"{','.join(w['has_reocr']) or 'none':>6}")
    print(f"\nWorklist written to: {args.out}")

    # flag any missing scans
    missing = [f for f in all_findings if not f["page_scans_present"]]
    if missing:
        print(f"\n[!] {len(missing)} segments have MISSING source scans "
              f"(re-OCR impossible without them) — review the worklist.")


if __name__ == "__main__":
    main()
