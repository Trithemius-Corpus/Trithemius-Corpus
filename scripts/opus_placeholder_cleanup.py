"""Opus placeholder cleanup — replace v2 thinking-mode placeholders with
Claude Opus 4.7 translations.

For each chunk file in `translations/minimax-v2/full/` that contains the
`<!-- skipped: ... -->` marker, this script:

  1. Deletes the placeholder .md file
  2. Invokes the working harness with --engine claude-cli + --claude-model
     claude-opus-4-7 + --engine-subdir minimax-v2 so the Opus translation
     lands in the same directory slot (effectively a per-chunk upgrade
     within the minimax-v2 backend tree)

The harness skips existing chunks automatically, so only the deleted
placeholder slots get re-translated.

Sharding: two shards split the affected works to allow 2 Opus workers
running in parallel. Worker 1 handles the single largest work
(prdl-70290), worker 2 handles all the others.

Usage:
    python scripts/opus_placeholder_cleanup.py --shard 1/2
    python scripts/opus_placeholder_cleanup.py --shard 2/2
    python scripts/opus_placeholder_cleanup.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "manifest.json"
PUBLIC_SCRIPTS = REPO / "scripts"

WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
HARNESS = WORKING / "scripts" / "latin_translation_harness.py"
CORPUS = WORKING / "data" / "corpus"
PYTHON_EXE = os.environ.get(
    "TRITHEMIUS_PYTHON",
    r"C:\Users\Ian\AppData\Local\Programs\Python\Python313\python.exe",
)

PLACEHOLDER_MARKERS = (
    "skipped: thinking_max_tokens",
    "skipped: short_output_retry_exhausted",
)

# Split affected works between two shards.
# Worker 1 owns the largest work alone; worker 2 owns the rest.
LARGE_WORK = "prdl-70290_opera-historica-part-chronicon-hirsaugiense-sponheimense"


def is_placeholder(md_path: Path) -> bool:
    try:
        head = md_path.read_text(encoding="utf-8", errors="replace")[:300]
    except Exception:
        return False
    return any(marker in head for marker in PLACEHOLDER_MARKERS)


def find_placeholders() -> dict[str, list[Path]]:
    """Return {work_id -> [placeholder paths]} for v2 outputs."""
    by_work: dict[str, list[Path]] = defaultdict(list)
    for work_dir in CORPUS.iterdir():
        v2_dir = work_dir / "translations" / "minimax-v2" / "full"
        if not v2_dir.is_dir():
            continue
        for f in sorted(v2_dir.glob("full_chunk_*.md")):
            if is_placeholder(f):
                by_work[work_dir.name].append(f)
    return by_work


def cluster_of(work_id: str) -> str | None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for w in m["works"]:
        if w["id"] == work_id:
            return w.get("genre_cluster")
    return None


def shard_works(works: list[str], idx: int, count: int) -> list[str]:
    """Worker 1 owns LARGE_WORK alone; worker 2 owns the rest."""
    if count != 2:
        # Generic hash-partition fallback
        import hashlib
        return [w for w in works if int(hashlib.sha256(w.encode()).hexdigest(), 16) % count == idx - 1]
    if idx == 1:
        return [w for w in works if w == LARGE_WORK]
    return [w for w in works if w != LARGE_WORK]


def run_one_work(work_id: str, dry_run: bool = False) -> dict:
    cluster = cluster_of(work_id)
    if not cluster:
        return {"work_id": work_id, "skipped": "no cluster"}

    full_txt = CORPUS / work_id / "full.txt"
    if not full_txt.exists():
        return {"work_id": work_id, "skipped": f"no {full_txt}"}

    out_root = CORPUS / work_id / "translations"

    cmd = [
        PYTHON_EXE, str(HARNESS),
        str(full_txt),
        "--engine", "claude-cli",
        "--claude-model", "claude-opus-4-7",
        "--max-output-tokens", "2048",
        "--temperature", "0.2",
        "--top-p", "0.6",
        "--max-chars", "4500",
        "--out-dir", str(out_root),
        "--engine-subdir", "minimax-v2",
        "--parallel", "1",  # one Opus call at a time per process
        "--timeout", "900",
        "--use-retrieval", "--use-vulgate", "--ocr-cleanup",
        "--cluster", cluster,
        "--public-repo-scripts", str(PUBLIC_SCRIPTS),
    ]

    if dry_run:
        print("DRY:", " ".join(cmd))
        return {"work_id": work_id, "dry": True}

    print(f"=== {work_id} (cluster={cluster}) ===", flush=True)
    proc = subprocess.run(cmd, cwd=WORKING)
    return {"work_id": work_id, "exit_code": proc.returncode}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", default="", help="INDEX/COUNT, e.g. 1/2")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    by_work = find_placeholders()
    affected_works = sorted(by_work.keys())
    total_placeholders = sum(len(v) for v in by_work.values())
    print(f"corpus-wide placeholders: {total_placeholders} across {len(affected_works)} works")
    for w in affected_works:
        print(f"  {len(by_work[w]):3d}  {w}")

    if args.shard:
        idx, count = (int(x) for x in args.shard.split("/"))
        my_works = shard_works(affected_works, idx, count)
        print(f"\nshard {idx}/{count}: {len(my_works)} works ({sum(len(by_work[w]) for w in my_works)} placeholders)")
    else:
        my_works = affected_works

    # Delete placeholders so the harness picks them up as missing chunks.
    if not args.dry_run:
        for w in my_works:
            for f in by_work[w]:
                f.unlink()
        print(f"\ndeleted {sum(len(by_work[w]) for w in my_works)} placeholder files")

    results = []
    for w in my_works:
        results.append(run_one_work(w, dry_run=args.dry_run))
    print(f"\n=== summary ===")
    for r in results:
        print(f"  {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
