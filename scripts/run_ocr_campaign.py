"""Long-running OCR campaign for the Trithemius corpus.

Walks the backlog in priority order (smallest gap first for quick wins),
running qwen3vl_ocr_batch.py per work. Resumable: skips works that are
already fully OCR'd. Saves campaign state to E:\\trithemius\\.hermes\\
so restarts pick up where they stopped.

Strategy:
- Iterate works in size order (smallest first; quick wins)
- Per work, run the existing qwen3vl_ocr_batch.py which is already
  resume-safe (it skips pages that already have OCR files)
- The campaign will re-scan the backlog after each work completes,
  so as the small works finish, larger works naturally get OCR'd next
- Logs every work to E:\\trithemius\\.hermes\\ocr-campaign-log.jsonl
- Writes the current backlog to E:\\trithemius\\.hermes\\ocr-backlog.json
  after every work (so progress is visible to a fresh session)

Usage:
    python scripts/run_ocr_campaign.py
    python scripts/run_ocr_campaign.py --max-works 5
    python scripts/run_ocr_campaign.py --engine qwen3vl-4b-trithemius-q6
    python scripts/run_ocr_campaign.py --parallel 1
    python scripts/run_ocr_campaign.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
OCR_SCRIPT = ROOT / "scripts" / "qwen3vl_ocr_batch.py"
HERMES_DIR = Path(r"E:\trithemius\.hermes")
HERMES_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = HERMES_DIR / "ocr-campaign-log.jsonl"
BACKLOG_PATH = HERMES_DIR / "ocr-backlog.json"

CORPUS = Path(r"E:\trithemius\data\corpus")
MANIFEST = ROOT / "manifest.json"
ENGINE = "qwen3vl-4b-trithemius-q6"


def read_manifest() -> list[dict]:
    with MANIFEST.open(encoding="utf-8") as f:
        m = json.load(f)
    return m["works"]


def have_ocr_pages(work_id: str) -> set[int]:
    """Pages that have OCR text, by reading the pipeline's full.txt marker list."""
    full = CORPUS / work_id / "translations" / "_reocr" / ENGINE / "full.txt"
    if not full.is_file():
        return set()
    txt = full.read_text(encoding="utf-8", errors="replace")
    return {int(m.group(1)) for m in re.finditer(r"^---\s*Page\s+0*(\d+)\s*---", txt, re.M)}


def have_image_pages(work_id: str) -> set[int]:
    p = CORPUS / work_id / "pages"
    if not p.is_dir():
        return set()
    pages = set()
    for f in os.listdir(p):
        m = re.match(r"page_(\d+)\.", f)
        if m:
            pages.add(int(m.group(1)))
    return pages


def build_backlog(works: list[dict]) -> list[dict]:
    """Returns list of {work, expected, have_ocr, have_imgs, missing[]}."""
    backlog = []
    for w in works:
        wid = w["id"]
        expected = w.get("page_count", 0)
        imgs = have_image_pages(wid)
        if not imgs:
            continue
        ocr = have_ocr_pages(wid)
        missing = sorted(imgs - ocr)
        if not missing:
            continue
        backlog.append({
            "work": wid,
            "expected": expected,
            "have_ocr": len(ocr),
            "have_imgs": len(imgs),
            "missing": missing,
            "missing_count": len(missing),
        })
    return sorted(backlog, key=lambda r: (r["missing_count"], r["work"]))


def write_backlog(backlog: list[dict]) -> None:
    summary = {
        "as_of": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_to_ocr": sum(r["missing_count"] for r in backlog),
        "n_works": len(backlog),
        "backlog": [
            {
                "work": r["work"],
                "expected": r["expected"],
                "have_ocr": r["have_ocr"],
                "have_imgs": r["have_imgs"],
                "missing_count": r["missing_count"],
            }
            for r in backlog
        ],
    }
    BACKLOG_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def log_event(work: str, missing_before: int, elapsed_s: float, ok_pages: int, fail_pages: int) -> None:
    entry = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "work": work,
        "missing_before": missing_before,
        "ok_pages": ok_pages,
        "fail_pages": fail_pages,
        "elapsed_seconds": round(elapsed_s, 1),
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_one_work(work_id: str, args: argparse.Namespace) -> tuple[int, float, int, int]:
    """Run qwen3vl_ocr_batch.py on one work. Returns (returncode, elapsed_s, ok_pages, fail_pages)."""
    cmd = [
        PYTHON, str(OCR_SCRIPT),
        "--work", work_id,
        "--engine", args.engine,
        "--max-tokens", str(args.max_tokens),
        "--ctx-size", str(args.ctx_size),
        "--parallel", str(args.parallel),
        "--image-tokens", "1024",
        "--split-parts", "1",
        "--page-timeout", "900",
        "--model", r"E:\trithemius\models\Qwen3-VL-4B-Trithemius-Q6_K.gguf",
        "--mmproj", r"E:\trithemius\models\mmproj-Qwen3-VL-4B-Trithemius-F16.gguf",
        "--no-mmproj-offload",
        "--prompt-file", str(ROOT / "data" / "prompts" / "qwen3vl_trithemius_ocr_only.txt"),
        "--extract-ocr-section",
    ]
    t0 = time.time()
    print(f"\n{'=' * 80}\nOCR: {work_id}\n{'=' * 80}")
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))
    elapsed = time.time() - t0
    # Parse summary file for ok/fail
    summary = ROOT / ".cache" / "qwen3vl-ocr" / "last_run_summary.json"
    ok, fail = 0, 0
    if summary.is_file():
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
            for row in data:
                if row.get("work") == work_id:
                    ok = row.get("ocred", 0)
                    fail = row.get("failed", 0)
                    break
        except Exception:
            pass
    return proc.returncode, elapsed, ok, fail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=ENGINE)
    ap.add_argument("--max-works", type=int, default=0, help="0 = all works in backlog; >0 = stop after N")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--ctx-size", type=int, default=8192)
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--dry-run", action="store_true", help="Just build the backlog and exit")
    args = ap.parse_args()

    works = read_manifest()
    backlog = build_backlog(works)
    write_backlog(backlog)

    total = sum(r["missing_count"] for r in backlog)
    print(f"OCR campaign: {len(backlog)} works, {total} pages to OCR")
    print(f"Backlog written to {BACKLOG_PATH}")
    if args.dry_run:
        for r in backlog[:20]:
            print(f"  {r['work']}: {r['missing_count']} pages")
        return 0

    if not backlog:
        print("Nothing to OCR. All works are complete.")
        return 0

    n_processed = 0
    overall_t0 = time.time()
    while True:
        # Re-read backlog each iteration in case external OCR filled some pages
        works = read_manifest()
        backlog = build_backlog(works)
        write_backlog(backlog)
        if not backlog:
            print("\nBacklog empty. Done.")
            break
        if args.max_works and n_processed >= args.max_works:
            print(f"\nReached --max-works={args.max_works}, stopping.")
            break
        # Pick the smallest
        target = backlog[0]
        work_id = target["work"]
        missing_before = target["missing_count"]
        rc, elapsed, ok, fail = run_one_work(work_id, args)
        log_event(work_id, missing_before, elapsed, ok, fail)
        n_processed += 1
        if rc != 0:
            print(f"!! {work_id} exited with code {rc}; pausing 5s and continuing")
            time.sleep(5)
        else:
            print(f"OK {work_id}: {ok} pages OCR'd in {elapsed:.0f}s ({ok / max(1, elapsed):.2f} pg/s)")

    total_elapsed = time.time() - overall_t0
    print(f"\nCampaign done: {n_processed} works processed in {total_elapsed / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
