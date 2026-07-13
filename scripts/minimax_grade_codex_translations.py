"""minimax Codex translation grader — final pre-release sweep.

Reads the per-work Codex GPT-5.5 dual-context translations
(<work>/translations/qwen3vl-trithemius-q6-dual-gpt55/full/) against
the Qwen3VL-4B-Trithemius OCR
(<work>/translations/_reocr/qwen3vl-4b-trithemius-q6/) and grades
faithfulness 1-5 plus a hallucinated flag via 6 parallel
minimax workers paced to stay under the API rate limit.

This is the LAST SWEEP BEFORE PUBLIC RELEASE.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ---- paths --------------------------------------------------------------

CORPUS = Path(r"E:\trithemius\data\corpus")
REPO = Path(r"E:\trithemius-corpus")
TRANSLATION_BACKEND = "qwen3vl-trithemius-q6-dual-gpt55"
OCR_ENGINE = "qwen3vl-4b-trithemius-q6"
OCR_SUBDIR = f"translations/_reocr/{OCR_ENGINE}"
TRANSLATION_SUBDIR = f"translations/{TRANSLATION_BACKEND}/full"

OUT_ROOT = REPO / "data" / "_quality_codex_minimax_grade"
OUT_ROOT.mkdir(parents=True, exist_ok=True)

SUMMARY_PATH = REPO / "data" / "_quality" / "codex_grade_minimax_summary.jsonl"
REPORT_PATH = REPO / "QWEN3VL_CODEX_GRADING_REPORT_2026-07-05.md"

PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)
PREAMBLE_PATTERNS = [
    r"^(Here is|Below is|This is the|I'll translate|Let me translate|Translation:|The following|Sure,? here|Of course,? here)",
    r"^(In order to|To translate|I will translate|You want me to)",
]
PREAMBLE_RE = re.compile("|".join(PREAMBLE_PATTERNS), re.I)

# ---- sampling -----------------------------------------------------------

# Position-stratified: pick first 2, middle 2, last 2 by default,
# scale up by sqrt(N) so large works don't dominate.
def pick_chunks(chunk_numbers: list[int], rng: random.Random) -> list[int]:
    n = len(chunk_numbers)
    if n == 0:
        return []
    if n <= 6:
        return list(chunk_numbers)

    # Target: ~ sqrt(N) * 2 (works out to ~10-25 chunks per work)
    target = max(6, min(25, int(round(2 * (n ** 0.5)))))
    # Position strata: 3 buckets (open / middle / late)
    bucket_size = n / 3
    picks: set[int] = set()

    def pick_at(idx: int) -> None:
        if 0 <= idx < n:
            picks.add(chunk_numbers[idx])

    if n <= 25:
        # small works: take every chunk roughly
        step = max(1, n // target)
        for j in range(0, n, step):
            pick_at(j)
        pick_at(n - 1)
    else:
        # bigger works: stratified
        per_bucket = max(2, target // 3)
        for b in range(3):
            start = int(round(b * bucket_size))
            end = int(round((b + 1) * bucket_size)) - 1
            # evenly spaced picks inside the bucket
            bucket_indices = list(range(start, min(end + 1, n)))
            if not bucket_indices:
                continue
            step = max(1, len(bucket_indices) // per_bucket)
            for j in range(0, len(bucket_indices), step):
                pick_at(bucket_indices[j])
            # always include the bucket boundary
            pick_at(end if b < 2 else n - 1)

    return sorted(picks)


# ---- grader client ------------------------------------------------------

def load_minimax_creds() -> tuple[str, str]:
    auth_path = os.path.expanduser("~/.hermes/auth.json")
    auth = json.loads(Path(auth_path).read_text())
    pool = auth["credential_pool"]["minimax"]
    cred = pool[0]
    return cred["access_token"], cred["base_url"]


GRADER_SYSTEM_PROMPT = """You are an independent faithfulness grader for machine-translated early-modern Latin prose and verse into modern English.

You will be shown:
  - The Latin source text (OCR output, may contain typos / ligature artifacts).
  - The English translation produced by Codex GPT-5.5 from that source.

Your job is to grade the translation's faithfulness to the Latin, not its literary quality.

Scoring rubric (return a single integer 1-5):
  5 = faithful, complete, structure preserved, no fabricated content, technical vocabulary handled correctly.
  4 = one minor issue, no substantive flaw.
  3 = one substantive flaw OR several minor issues.
  2 = multiple substantive flaws (e.g. significant omission AND a transcription error).
  1 = fabricated, garbled, severely truncated, or wholesale topic-shift.

Also flag hallucination: true if the English introduces claims or details NOT present in (or strongly inferable from) the Latin source. Mark unclear-pass-through (e.g. "[unclear]") as faithful, not hallucinated. Mark plausible inference (e.g. expanding an abbreviation) as faithful. Mark INVENTED names, dates, or events as hallucinated.

Return a compact JSON object with these fields and NOTHING ELSE:
  {"faithful": <int 1-5>, "hallucinated": <bool>, "issues": [<str>, ...], "reason": "<one short sentence>"}

Use "issues" tags from this list, appended as needed:
  preamble_leak | marker_mismatch | heavy_nonascii | repetition_loop |
  faithful_omission | faithful_mistranslation | factual_hallucination |
  structural_break (page markers / list / rubric dropped) |
  technical_vocab_error (monastic / historical / cipher / occult term mishandled) |
  ocr_gated (Latin source is so damaged that translation fidelity is not really gradeable - mark faithful as 4 only if translator added [unclear] markers, else 3)

Output JSON only. No prose, no markdown, no explanation outside the JSON."""


GRADER_USER_PROMPT_TEMPLATE = """=== WORK ===
{work}

=== CHUNK {chunk} (pages {pages}) ===

=== LATIN SOURCE (Qwen3VL OCR) ===
{latin}

=== ENGLISH TRANSLATION (Codex GPT-5.5) ===
{english}

=== PRELIMINARY AUTOMATED CHECKS ===
{prelim}

Grade and return JSON only.
"""


def prelim_checks(english: str, expected_pages: list[int]) -> dict:
    issues = []
    if not english.strip():
        return {"valid": False, "issues": ["empty"]}
    first = english[:200].strip()
    if PREAMBLE_RE.search(first):
        issues.append("preamble_leak")
    n_markers = len(PAGE_RE.findall(english))
    if expected_pages and n_markers != len(expected_pages):
        issues.append(f"markers={n_markers}/pages={len(expected_pages)}")
    non_ascii = sum(1 for c in english if ord(c) > 127)
    if non_ascii > 0.1 * len(english):
        issues.append("heavy_nonascii")
    # Repetition heuristic: 50+ char window repeated within text
    if len(english) > 1200:
        for window_size in (50, 100, 200):
            wcount: dict[str, int] = defaultdict(int)
            for j in range(0, len(english) - window_size, 25):
                wcount[english[j:j + window_size]] += 1
            top = max(wcount.values()) if wcount else 0
            if top >= 5:
                issues.append(f"repetition_loop(w{window_size}x{top})")
                break
    return {"valid": True, "issues": issues, "chars": len(english), "non_ascii": non_ascii}


def call_minimax(key: str, base: str, system: str, user: str,
                  model: str, max_tokens: int, attempt: int = 0) -> dict:
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
        "system": system,
    }
    req = urllib.request.Request(
        f"{base}/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        data=json.dumps(body).encode("utf-8"),
    )
    try:
        r = urllib.request.urlopen(req, timeout=120)
        payload = json.loads(r.read())
        return payload
    except urllib.error.HTTPError as e:
        if e.code in (429, 500, 502, 503, 504) and attempt < 4:
            wait = 2 ** attempt + random.uniform(0, 1.5)
            time.sleep(wait)
            return call_minimax(key, base, system, user, model, max_tokens, attempt + 1)
        raise


def grade_one_chunk(work: str, chunk_n: int, latin_pages_text: str,
                    english_text: str, expected_pages: list[int],
                    key: str, base: str, model: str, max_tokens: int) -> dict:
    prelim = prelim_checks(english_text, expected_pages)
    if not prelim.get("valid"):
        return {
            "work": work, "chunk": chunk_n, "pages": expected_pages,
            "faithful": 1, "hallucinated": True,
            "issues": prelim["issues"], "reason": "empty translation",
            "prelim": prelim, "model": model,
        }
    user = GRADER_USER_PROMPT_TEMPLATE.format(
        work=work, chunk=chunk_n, pages=expected_pages,
        latin=latin_pages_text[:9000],
        english=english_text[:9000],
        prelim=json.dumps(prelim),
    )
    raw = call_minimax(key, base, GRADER_SYSTEM_PROMPT, user, model, max_tokens)
    text = "".join(b.get("text", "") for b in raw.get("content", []) if b.get("type") == "text")
    text = text.strip()
    # Strip code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.M).strip()
    # Find the first {...}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    parsed = None
    if m:
        try:
            parsed = json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    if not isinstance(parsed, dict):
        # Treat the grader output as a free-text failure
        return {
            "work": work, "chunk": chunk_n, "pages": expected_pages,
            "faithful": 0, "hallucinated": False,
            "issues": ["grader_parse_error"],
            "reason": text[:300],
            "prelim": prelim, "model": model,
            "usage": raw.get("usage"),
        }
    # Normalize fields
    faithful = int(parsed.get("faithful", 0))
    faithful = max(1, min(5, faithful))
    hallu = bool(parsed.get("hallucinated", False))
    issues = list(parsed.get("issues", []))
    # Re-merge prelim issues ONLY if the prelim check actually fired them.
    # Note: `markers=` is a numeric mismatch tag the prelim DID fire; `heavy_nonascii`
    # is also valid from the prelim ONLY if non_ascii > 10%. Re-check.
    prelim_set = set()
    if not prelim.get("valid"):
        prelim_set.update(prelim.get("issues", []))
    else:
        # Re-derive prelim tags definitively
        if any(i.startswith("markers=") for i in prelim.get("issues", [])):
            prelim_set.update(i for i in prelim["issues"] if i.startswith("markers="))
        if any(i.startswith("repetition_loop") for i in prelim.get("issues", [])):
            prelim_set.update(i for i in prelim["issues"] if i.startswith("repetition_loop"))
        # heavy_nonascii should only fire if non_ascii / chars > 0.10
        chars = prelim.get("chars", 1)
        if prelim.get("non_ascii", 0) > 0.10 * chars:
            prelim_set.add("heavy_nonascii")
        if "preamble_leak" in prelim.get("issues", []):
            prelim_set.add("preamble_leak")
    issues_merged: list[str] = []
    for it in issues:
        if it not in issues_merged:
            issues_merged.append(it)
    for pi in prelim_set:
        if not any(pi.split("(")[0] == ip.split("(")[0] for ip in issues_merged):
            issues_merged.append(pi)
    issues = issues_merged
    return {
        "work": work, "chunk": chunk_n, "pages": expected_pages,
        "faithful": faithful, "hallucinated": hallu,
        "issues": issues, "reason": parsed.get("reason", ""),
        "prelim": prelim, "model": model,
        "usage": raw.get("usage"),
    }


# ---- work loading -------------------------------------------------------

def load_work_chunks(work: str) -> dict[int, dict]:
    tdir = CORPUS / work / TRANSLATION_SUBDIR
    runs_path = tdir / "runs.jsonl"
    if not runs_path.is_file():
        return {}
    out: dict[int, dict] = {}
    for line in runs_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        chunk_n = int(row["chunk"])
        md = tdir / f"full_chunk_{chunk_n:04d}.md"
        if md.is_file():
            out[chunk_n] = row
    return out


def get_ocr_pages_text(work: str, page_nums: list[int]) -> str:
    base = CORPUS / work / OCR_SUBDIR
    chunks: list[str] = []
    for p in page_nums:
        path = base / f"page_{p:03d}.txt"
        if path.is_file():
            chunks.append(f"--- Page {p:03d} ---\n{path.read_text(encoding='utf-8', errors='replace')}")
    return "\n\n".join(chunks)


def get_chunk_english(work: str, chunk_n: int) -> str:
    return (CORPUS / work / TRANSLATION_SUBDIR / f"full_chunk_{chunk_n:04d}.md").read_text(
        encoding="utf-8", errors="replace"
    )


# ---- worker -------------------------------------------------------------

def worker(worker_id: int, queue: list[dict], key: str, base: str,
            model: str, max_tokens: int, pace_s: float,
            lock: threading.Lock, progress: dict, sink: dict[str, list[dict]],
            work_files: dict[str, Path]):
    rng = random.Random(worker_id * 7919 + 1)
    while True:
        with lock:
            if not queue:
                return
            item = queue.pop()
            progress["remaining"] = len(queue)
            progress["active_workers"] += 1
        work = item["work"]; chunk_n = item["chunk"]
        try:
            row = item["row"]
            expected_pages = sorted(int(p) for p in row.get("pages", []))
            english = item["english"]
            latin = item["latin"]
            res = grade_one_chunk(work, chunk_n, latin, english,
                                    expected_pages, key, base, model, max_tokens)
            sink.setdefault(work, []).append(res)
            # Incremental flush: append to per-work file immediately so we
            # don't lose progress if the process dies.
            with lock:
                wf = work_files[work]
                with wf.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(res, ensure_ascii=False) + "\n")
        except Exception as e:
            sink.setdefault(work, []).append({
                "work": work, "chunk": chunk_n,
                "pages": item["row"].get("pages", []),
                "faithful": 0, "hallucinated": False,
                "issues": ["grader_call_error"],
                "reason": f"{type(e).__name__}: {e}"[:300],
                "model": model,
            })
            with lock:
                wf = work_files[work]
                with wf.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({
                        "work": work, "chunk": chunk_n,
                        "pages": item["row"].get("pages", []),
                        "faithful": 0, "hallucinated": False,
                        "issues": ["grader_call_error"],
                        "reason": f"{type(e).__name__}: {e}"[:300],
                        "model": model,
                    }, ensure_ascii=False) + "\n")
        finally:
            with lock:
                progress["active_workers"] -= 1
        # Pace between calls per worker (not global)
        time.sleep(pace_s + rng.uniform(0, 0.3))


# ---- per-work output ----------------------------------------------------

def write_work_artifacts(work: str, graded: list[dict], sampled: list[int],
                         all_chunk_count: int, total_chars: int):
    wdir = OUT_ROOT / work
    wdir.mkdir(parents=True, exist_ok=True)
    jsonl = wdir / "graded_chunks.jsonl"
    with jsonl.open("w", encoding="utf-8") as fh:
        for r in graded:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    sampling_md = wdir / "SAMPLING.md"
    lines = [
        f"# Sampling — {work}",
        "",
        f"- Total chunks on disk: {all_chunk_count}",
        f"- Total Latin input chars: {total_chars:,}",
        f"- Chunks sampled: {len(sampled)} ({len(sampled) / max(1, all_chunk_count) * 100:.1f}%)",
        f"- Sampled chunk numbers: {sampled}",
        f"- Graded (post-run): {len(graded)}",
        "",
    ]
    sampling_md.write_text("\n".join(lines), encoding="utf-8")
    return jsonl


# ---- main ---------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status-file", default=str(REPO / ".cache" / "qwen3vl-corpus-pipeline" / "status-20260705-191330.json"))
    ap.add_argument("--model", default="MiniMax-M3")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--pace", type=float, default=2.0, help="seconds between calls per worker")
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260705)
    ap.add_argument("--limit-works", type=int, default=0,
                    help="if >0, only process the first N works (for debugging pacing)")
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    status = json.loads(Path(args.status_file).read_text())
    works = [s["work"] for s in status]
    if args.limit_works > 0:
        works = works[:args.limit_works]
    print(f"[setup] {len(works)} works")

    key, base = load_minimax_creds()
    print(f"[setup] minimax endpoint OK; model={args.model}, workers={args.workers}, pace={args.pace}s")

    # Build the work queue
    queue: list[dict] = []
    sample_lists: dict[str, list[int]] = {}
    work_meta: dict[str, dict] = {}
    for s in status:
        work = s["work"]
        if work not in works:
            continue
        chunks_map = load_work_chunks(work)
        if not chunks_map:
            print(f"[warn] no chunks for {work}")
            continue
        chunk_nums = sorted(chunks_map)
        picked = pick_chunks(chunk_nums, rng)
        sample_lists[work] = picked
        work_meta[work] = {"all_chunk_count": len(chunk_nums),
                           "reported_chunks": s["translated_chunks"],
                           "pages": s["pages"],
                           "full_chars": s["full_chars"]}
        for cn in picked:
            row = chunks_map[cn]
            english = get_chunk_english(work, cn)
            latin = get_ocr_pages_text(work, sorted(int(p) for p in row.get("pages", [])))
            queue.append({"work": work, "chunk": cn, "row": row,
                          "english": english, "latin": latin})
    total = len(queue)
    print(f"[setup] {total} chunks queued across {len(works)} works")

    # Build per-work jsonl targets ahead of time so workers can append incrementally
    work_files: dict[str, Path] = {}
    seen_works: set[str] = set()
    for item in queue:
        w = item["work"]
        if w in seen_works:
            continue
        seen_works.add(w)
        wdir = OUT_ROOT / w
        wdir.mkdir(parents=True, exist_ok=True)
        work_files[w] = wdir / "graded_chunks.jsonl"

    sink: dict[str, list[dict]] = {}
    lock = threading.Lock()
    progress = {"remaining": total, "active_workers": 0, "completed": 0}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(worker, i, queue, key, base, args.model,
                             args.max_tokens, args.pace, lock, progress, sink,
                             work_files)
                 for i in range(args.workers)]


    # NOTE: per-work jsonl files are now written incrementally by the workers;
    # write_work_artifacts() later only updates SAMPLING.md and refreshes
    # graded_chunks.jsonl from the sink (idempotent overwrite from in-memory data).

    # Periodic progress reporter
    done_event = threading.Event()
    def reporter():
        while not done_event.is_set():
            time.sleep(10)
            with lock:
                rem = progress["remaining"]
                done = progress["completed"]
                active = progress["active_workers"]
            elapsed = time.time() - t0
            rate = (total - rem) / max(elapsed, 1e-3)
            eta = rem / max(rate, 1e-3) / 60
            print(f"[progress] done={total - rem}/{total} active={active} "
                  f"rate={rate:.2f}/s eta={eta:.1f}min", flush=True)
            progress["completed"] = total - rem
    rep_thread = threading.Thread(target=reporter, daemon=True)
    rep_thread.start()
    for f in as_completed(futs):
        f.result()  # raises if any worker crashed
    done_event.set()

    elapsed = time.time() - t0
    print(f"[done] graded {total - progress['remaining']} chunks in {elapsed/60:.1f} min")

    # Write per-work outputs
    summary_rows = []
    for work in works:
        graded = sorted(sink.get(work, []), key=lambda r: r["chunk"])
        meta = work_meta.get(work, {})
        write_work_artifacts(work, graded, sample_lists.get(work, []),
                              meta.get("all_chunk_count", 0), meta.get("full_chars", 0))
        # Compute per-work rollup
        n = len(graded)
        valid = [g for g in graded if g["faithful"] > 0]
        mean_faith = (sum(g["faithful"] for g in valid) / max(len(valid), 1)) if valid else 0
        n_hallu = sum(1 for g in graded if g.get("hallucinated"))
        hall_rate = (n_hallu / max(n, 1)) * 100
        # Tier per METHODOLOGY
        if mean_faith >= 4.0 and hall_rate <= 5:
            tier = "S"
        elif mean_faith >= 3.5 and hall_rate <= 15:
            tier = "A"
        elif mean_faith >= 3.0 and hall_rate <= 30:
            tier = "B"
        elif mean_faith >= 2.5:
            tier = "C"
        else:
            tier = "F"
        summary_rows.append({
            "work": work,
            "sampled_chunks": n,
            "population_chunks": meta.get("all_chunk_count", 0),
            "sample_pct": (n / max(meta.get("all_chunk_count", 1), 1)) * 100,
            "pages": meta.get("pages", 0),
            "full_chars": meta.get("full_chars", 0),
            "mean_faithful": round(mean_faith, 3),
            "hallucinated_chunks": n_hallu,
            "hallucination_pct": round(hall_rate, 2),
            "tier": tier,
            "issues_summary": _issues_summary(graded),
        })

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Merge with any existing summary rows for works not in this run.
    # Without this, a `--limit-works N < 47` smoke would clobber the full rollup.
    existing_rows: list[dict] = []
    if SUMMARY_PATH.exists():
        for line in SUMMARY_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    existing_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    processed_works = {r["work"] for r in summary_rows}
    keep_rows = [r for r in existing_rows if r["work"] not in processed_works]
    merged_rows = summary_rows + keep_rows  # processed first so they take priority
    merged_rows.sort(key=lambda r: r["work"])
    with SUMMARY_PATH.open("w", encoding="utf-8") as fh:
        for r in merged_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[done] wrote {SUMMARY_PATH} (merged: {len(summary_rows)} new + {len(keep_rows)} kept = {len(merged_rows)} total)")
    return 0


def _issues_summary(graded: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for g in graded:
        for it in g.get("issues", []):
            tag = it.split("(")[0]
            counts[tag] += 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
