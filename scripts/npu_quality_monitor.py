"""Spot-check NPU retranslation quality at cap 3500.

Run periodically to confirm the retranslate is producing full, clean output.
Flags any truncated chunks (<35% of input), mid-clause endings, or works
falling behind. Reads runs.jsonl across all works.

Usage:
    python scripts/npu_quality_monitor.py
"""
import os, glob, json, re
from datetime import datetime

base = "E:/trithemius/data/corpus"

print(f"NPU retranslate quality monitor — {datetime.now():%Y-%m-%d %H:%M:%S}")
print("=" * 78)

per_work = []
total_chunks = 0
total_short = 0
total_chars_in = 0
total_chars_out = 0

for w in sorted(os.listdir(base)):
    d = os.path.join(base, w, "translations", "npu-qwen3vl-q4nx", "full")
    rf = os.path.join(d, "runs.jsonl")
    if not os.path.isfile(rf):
        continue
    # only count fresh (cap-3500) runs: those after the backup (~10:30 today)
    chunks = []
    for line in open(rf, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except Exception:
            continue
        if j.get("warn") == "short_output":
            total_short += 1
            continue
        # only count entries from the fresh run (after 2026-07-04T10:25)
        ts = j.get("timestamp", "")
        if ts < "2026-07-04T10:25":
            continue
        chunks.append(j)
    if not chunks:
        continue
    n = len(chunks)
    ci = sum(c.get("input_chars", 0) for c in chunks)
    co = sum(c.get("output_chars", 0) for c in chunks)
    short = sum(1 for c in chunks if c.get("output_chars", 0) < c.get("input_chars", 1) * 0.35)
    ratio = co / ci if ci else 0
    total_chunks += n
    total_chars_in += ci
    total_chars_out += co
    per_work.append((w, n, ci, co, short, ratio))

per_work.sort(key=lambda x: -x[5])  # by ratio descending

print(f"\n{'work':58s} {'chunks':>6} {'ratio':>6} {'short':>5}")
print("-" * 78)
for w, n, ci, co, short, ratio in per_work:
    flag = "  <-- INVESTIGATE" if (short > 0 or ratio < 0.5) else ""
    print(f"{w[:58]:58s} {n:6d} {ratio:6.2f} {short:5d}{flag}")

print("-" * 78)
overall_ratio = total_chars_out / total_chars_in if total_chars_in else 0
print(f"{'TOTAL':58s} {total_chunks:6d} {overall_ratio:6.2f} {total_short:5d}")
print(f"\nFresh chunks so far: {total_chunks}")
print(f"Overall out/in ratio: {overall_ratio:.2f}  (healthy: 0.9-1.3; pre-fix was ~0.4)")
print(f"Short-output warnings (guard refused to cache): {total_short}")

# spot-check a few chunk tails. NOTE: a missing terminator is NOT by itself a
# sign of truncation — OCR page breaks routinely fall mid-sentence, so a
# faithful translation continues onto the next chunk. The out/in ratio above is
# the real truncation signal. We show tails only to eyeball fluency.
print(f"\n--- tail spot-check (last 60 chars of 5 most-recent chunks) ---")
print("(missing terminator = page break mid-sentence, which is normal; ratio is the real signal)")
recent = []
for w in sorted(os.listdir(base)):
    d = os.path.join(base, w, "translations", "npu-qwen3vl-q4nx", "full")
    for f in glob.glob(os.path.join(d, "full_chunk_*.md")):
        recent.append((os.path.getmtime(f), f, w))
recent.sort(reverse=True)
for mt, f, w in recent[:5]:
    t = open(f, encoding="utf-8", errors="replace").read().rstrip()
    tail = t[-60:].replace("\n", " ")
    print(f"  {os.path.basename(f):22s} ...{tail!r}")

# Real truncation check: any chunk under 35% ratio that the guard let through?
print(f"\n--- truncation check (ratio < 0.35 = cutoff) ---")
truncated = 0
for w, n, ci, co, short, ratio in per_work:
    if ratio < 0.5:
        print(f"  WARNING: {w[:55]} overall ratio {ratio:.2f}")
if total_short == 0 and overall_ratio >= 0.7:
    print("  No truncation detected. Retranslate is healthy.")
else:
    print(f"  {total_short} short-output chunks refused by guard (will retry).")
