"""Translate a work's Qwen-3VL-OCR'd full.txt to English using Claude via
the `claude` CLI (Anthropic), writing to a fable5-style translation backend.

Why a dedicated driver instead of just translate_corpus.py:
- We want to drive fable5 as a *parallel lane* to codex without
  disturbing the codex pipeline state
- fable5 is a different API family (Anthropic) with its own
  rate limits; we want to keep its state isolated
- This driver reuses latin_translation_harness.py with --engine
  claude-cli, which we know works (run_claude_cli at line 738)

The output is a standard full_chunk_NNNN.md + runs.jsonl per work,
same shape as codex and Qwen-4B outputs, so the dual-grade
infrastructure (dual_grade_codex_vs_qwen.py) will work after we
tweak it to handle the fable5 backend.

Usage:
    python scripts/translate_with_fable5.py \
        --work prdl-24389_polygraphiae-libri-sex-ioannis-trithemii-abbatis \
        --out-backend fable5-full \
        --claude-model claude-sonnet-4-5 \
        --max-chars 4500
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRITHEMIUS = Path(r"E:\trithemius")
HARNESS = TRITHEMIUS / "scripts" / "latin_translation_harness.py"
CORPUS = TRITHEMIUS / "data" / "corpus"
OCR_ENGINE = "qwen3vl-4b-trithemius-q6"

PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)


def chunk_text(text: str, max_chars: int) -> list[tuple[list[int], str]]:
    """Split at page markers; never split inside a page."""
    parts = re.split(r"(^---\s*Page\s+\d+\s*---\s*$)", text, flags=re.M)
    pages = []
    cur_page = 0
    cur_body = ""
    i = 0
    if parts and parts[0].strip() == "":
        i = 1
    while i < len(parts):
        marker = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        m = re.match(r"^---\s*Page\s+0*(\d+)\s*---\s*$", marker)
        if m:
            cur_page = int(m.group(1))
            cur_body = body
        else:
            cur_body = marker + "\n" + body
        if cur_body.strip():
            pages.append((cur_page, cur_body))
        i += 2
    chunks = []
    cur_pages = []
    cur_text = ""
    for pn, body in pages:
        marker = f"--- Page {pn:03d} ---\n"
        candidate = (cur_text + "\n" if cur_text else "") + marker + body
        if len(candidate) > max_chars and cur_pages:
            chunks.append((cur_pages, cur_text))
            cur_pages = [pn]
            cur_text = marker + body
        else:
            cur_pages.append(pn)
            cur_text = candidate
    if cur_pages:
        chunks.append((cur_pages, cur_text))
    return chunks


def call_claude_harness(input_path: Path, out_dir: Path, model: str, timeout: int) -> tuple[int, str]:
    """Invoke latin_translation_harness.py with --engine claude-cli.

    The harness writes each chunk to
    <out-dir>/claude-cli/<input-stem>/<input-stem>_chunk_NNNN.md
    (out_dir = resolve_path(args.out_dir) / engine_subdir / source_name).
    We point --out-dir at a per-chunk temp dir and read the chunk back
    from that nested path.
    """
    cmd = [
        sys.executable, str(HARNESS),
        str(input_path),
        "--engine", "claude-cli",
        "--claude-model", model,
        "--max-chars", "4500",
        "--out-dir", str(out_dir),
        "--parallel", "1",
        "--timeout", str(timeout),
        "--max-output-tokens", "2000",
        "--temperature", "0.2",
        "--top-p", "0.6",
    ]
    print(f"  [harness] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(TRITHEMIUS), capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    return proc.returncode, (proc.stdout + "\n--- stderr ---\n" + proc.stderr)[-4000:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, action="append", help="Work id (folder name under data/corpus/). Repeatable.")
    ap.add_argument("--out-backend", required=True, help="Subdir under translations/ to write fable5 output to")
    ap.add_argument("--claude-model", default="claude-sonnet-4-5", help="Model ID passed to the claude CLI")
    ap.add_argument("--max-chars", type=int, default=4500)
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--top-p", type=float, default=0.6)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--force", action="store_true", help="Re-translate even if chunk exists")
    args = ap.parse_args()

    overall_t0 = time.time()
    for work_id in args.work:
        work_dir = CORPUS / work_id
        if not work_dir.is_dir():
            print(f"!! {work_id}: work dir not found, skipping")
            continue
        ocr_full = work_dir / "translations" / "_reocr" / OCR_ENGINE / "full.txt"
        if not ocr_full.is_file():
            print(f"!! {work_id}: OCR full.txt not found at {ocr_full}, skipping")
            continue
        out_dir = work_dir / "translations" / args.out_backend / "full"
        out_dir.mkdir(parents=True, exist_ok=True)
        runs_path = out_dir / "runs.jsonl"

        latin = ocr_full.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_text(latin, args.max_chars)
        print(f"\n=== {work_id}: {len(chunks)} chunks (max_chars={args.max_chars}) ===")

        n_ok, n_skip, n_fail = 0, 0, 0
        t0 = time.time()
        for idx, (pages, chunk_value) in enumerate(chunks, start=1):
            out_path = out_dir / f"full_chunk_{idx:04d}.md"
            if out_path.exists() and not args.force:
                n_skip += 1
                print(f"  [{idx}/{len(chunks)}] skip (exists): pages={pages}")
                continue
            # Write a single-chunk OCR file that the harness will read
            tmp_input = out_dir / f"_tmp_input_{idx:04d}.txt"
            tmp_input.write_text(chunk_value, encoding="utf-8")
            tmp_output_dir = out_dir / f"_tmp_harness_{idx:04d}"
            tmp_output_dir.mkdir(parents=True, exist_ok=True)
            try:
                rc, tail = call_claude_harness(tmp_input, tmp_output_dir,
                                              args.claude_model, args.timeout)
                if rc != 0:
                    n_fail += 1
                    print(f"  [{idx}/{len(chunks)}] FAIL pages={pages}: harness exit {rc}")
                    print(tail[-2000:])
                    continue
                # Harness output lands at <out-dir>/claude-cli/<stem>/<stem>_chunk_0001.md
                stem = tmp_input.stem
                harness_out = tmp_output_dir / "claude-cli" / stem / f"{stem}_chunk_0001.md"
                if not harness_out.is_file():
                    n_fail += 1
                    print(f"  [{idx}/{len(chunks)}] FAIL pages={pages}: harness wrote nothing")
                    continue
                english = harness_out.read_text(encoding="utf-8", errors="replace").strip()
                out_path.write_text(english + "\n", encoding="utf-8")
                n_ok += 1
                elapsed = time.time() - t0
                print(f"  [{idx}/{len(chunks)}] ok pages={pages} latin={len(chunk_value)} english={len(english)} total={elapsed:.0f}s")
                with runs_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "chunk": idx,
                        "pages": pages,
                        "input_chars": len(chunk_value),
                        "output_chars": len(english),
                        "engine": "claude-cli",
                        "translator": args.claude_model,
                        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                    }, ensure_ascii=False) + "\n")
            finally:
                tmp_input.unlink(missing_ok=True)
                shutil.rmtree(tmp_output_dir, ignore_errors=True)
        total = time.time() - t0
        print(f"--- {work_id}: ok={n_ok} skip={n_skip} fail={n_fail} total={total:.0f}s ---")
    print(f"\nAll works done in {(time.time() - overall_t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
