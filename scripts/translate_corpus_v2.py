"""v2 translation driver — cluster-aware, public-domain retrieval anchors only.

For each non-skipped work in manifest.json:
  1. Read the genre_cluster assignment
  2. Locate the existing OCR'd full.txt in the working corpus dir
  3. Invoke the patched harness with --cluster <cluster> --public-repo-scripts <path>
     so retrieval uses data/retrieval/<cluster>/ (PD-only anchors)
  4. Write outputs to <working>/data/corpus/<id>/translations/minimax-v2/
  5. Track per-work progress in progress.minimax-v2.json

The v1 outputs in translations/{minimax,claude-cli,llama-server}/ are not
touched; the canonical-backend selection in the calibrated scoreboard will
pick whichever backend scores highest per work.

Prerequisites:
  - python scripts/build_retrieval_index.py  (one-time, builds the indices)
  - manifest.json present at repo root with genre_cluster per work
  - WORKING/data/corpus/<id>/full.txt exists for every translatable work
  - WORKING/scripts/latin_translation_harness.py has the v2 --cluster patch

Usage:
    python scripts/translate_corpus_v2.py
    python scripts/translate_corpus_v2.py --only prdl-24389_polygraphiae-libri-sex
    python scripts/translate_corpus_v2.py --max-works 3 --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "manifest.json"
PUBLIC_SCRIPTS = REPO / "scripts"

# Working-dir paths — where v1 was produced and where v2 outputs land.
# The working dir is referenced by an env override; default is E:\trithemius.
WORKING = Path(__import__("os").environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"
HARNESS = WORKING / "scripts" / "latin_translation_harness.py"
PYTHON_EXE = __import__("os").environ.get(
    "TRITHEMIUS_PYTHON",
    r"C:\Users\Ian\AppData\Local\Programs\Python\Python313\python.exe",
)

BACKEND_TAG = "minimax-v2"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest() -> list[dict]:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return m["works"]


def progress_path(work_id: str) -> Path:
    return CORPUS / work_id / f"progress.{BACKEND_TAG}.json"


def load_progress(work_id: str) -> dict:
    p = progress_path(work_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_progress(work_id: str, prog: dict) -> None:
    p = progress_path(work_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(prog, indent=2), encoding="utf-8")


def work_complete(work_id: str) -> bool:
    return load_progress(work_id).get("status") == "complete"


def translate_work(work: dict, timeout: int, max_output_tokens: int,
                   temperature: float, top_p: float, parallel: int,
                   minimax_model: str) -> dict:
    work_id = work["id"]
    cluster = work.get("genre_cluster")
    if not cluster:
        return {"exit_code": 99, "seconds": 0.0, "skipped": "no cluster"}

    full_txt = CORPUS / work_id / "full.txt"
    if not full_txt.exists():
        return {"exit_code": 98, "seconds": 0.0, "skipped": f"no full.txt at {full_txt}"}

    out_root = CORPUS / work_id / "translations"
    cmd = [
        PYTHON_EXE, str(HARNESS),
        str(full_txt),
        "--engine", "minimax",
        "--minimax-model", minimax_model,
        "--max-output-tokens", str(max_output_tokens),
        "--temperature", str(temperature),
        "--top-p", str(top_p),
        "--max-chars", str(4500),
        "--out-dir", str(out_root),
        "--engine-subdir", BACKEND_TAG,
        "--parallel", str(parallel),
        "--timeout", str(timeout),
        "--use-retrieval",
        "--use-vulgate",
        "--ocr-cleanup",
        # Lever D (--refine-on-bad-grade) is implemented in the harness but DISABLED
        # by default for v2.0 — smoke testing on the cipher-heavy bald-men ecloga
        # found the refine pass degraded translations (regrade < first-pass grade).
        # Either the refine prompt confuses the model or the grader is inconsistent
        # enough that regrade signals are unreliable. Re-enable in v2.1 once Lever D
        # is tuned with a keep-better-grade safety wrapper. See task 24.
        "--cluster", cluster,
        "--public-repo-scripts", str(PUBLIC_SCRIPTS),
    ]
    started = time.time()
    proc = subprocess.run(cmd, cwd=WORKING)
    elapsed = time.time() - started
    return {"exit_code": proc.returncode, "seconds": round(elapsed, 1)}


def parse_shard(value: str) -> tuple[int, int] | None:
    """Parse a 'INDEX/COUNT' shard spec, e.g. '1/3' or '2/3'."""
    if not value:
        return None
    parts = value.split("/")
    if len(parts) != 2:
        raise SystemExit(f"--shard must be INDEX/COUNT, got {value!r}")
    idx, count = int(parts[0]), int(parts[1])
    if not (1 <= idx <= count) or count < 1:
        raise SystemExit(f"--shard {value} out of range (idx in [1,count])")
    return idx, count


def apply_shard(works: list[dict], shard: tuple[int, int] | None) -> list[dict]:
    """Deterministically partition works into COUNT shards (by hash of id) and
    return only those belonging to INDEX. Lets multiple driver processes run in
    parallel without coordinating on which work they own."""
    if shard is None:
        return works
    idx, count = shard
    import hashlib
    out = []
    for w in works:
        h = int(hashlib.sha256(w["id"].encode("utf-8")).hexdigest(), 16)
        if (h % count) == (idx - 1):
            out.append(w)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="v2 cluster-aware re-translation driver.")
    parser.add_argument("--only", default="", help="Translate only this work ID.")
    parser.add_argument("--max-works", type=int, default=0, help="Stop after this many works.")
    parser.add_argument("--dry-run", action="store_true", help="List the plan and exit.")
    parser.add_argument("--parallel", type=int, default=16,
                        help="Concurrent in-flight chunks per process. Default 16 (was 8 in v2.0 pilot). "
                             "Bump higher only if MiniMax rate limits aren't being hit.")
    parser.add_argument("--shard", default="",
                        help="Run only a hash-partitioned shard (e.g. '1/3'). Lets multiple "
                             "translate_corpus_v2.py processes run in parallel without overlap.")
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.6)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--minimax-model", default="MiniMax-M2.7")
    args = parser.parse_args()

    if not HARNESS.exists():
        print(f"ERROR: harness not found at {HARNESS}", file=sys.stderr)
        print(f"  Set TRITHEMIUS_WORKING env var to override.", file=sys.stderr)
        return 1

    shard = parse_shard(args.shard)
    works = load_manifest()
    works = [w for w in works if not w["skip"]]
    works = apply_shard(works, shard)
    if args.only:
        works = [w for w in works if w["id"] == args.only]
    pending = [w for w in works if not work_complete(w["id"])]
    if args.max_works:
        pending = pending[: args.max_works]
    if shard:
        print(f"shard: {shard[0]}/{shard[1]}  ({len(works)} works in this shard)")

    print(f"manifest: {len(works)} translatable works · {len(pending)} pending v2")
    for w in pending:
        marker = "·" if work_complete(w["id"]) else " "
        print(f"  {marker} cluster={w.get('genre_cluster','?'):20} pri={w.get('priority',99):>2} {w['id']}")

    if args.dry_run:
        print("\n--dry-run set; exiting without translating.")
        return 0

    if not pending:
        print("\nnothing to do.")
        return 0

    overall_started = time.time()
    for w in pending:
        prog = load_progress(w["id"]) or {"id": w["id"], "events": []}
        prog["events"].append({"ts": utcnow(), "stage": "v2_start"})
        prog["status"] = "in_progress"
        save_progress(w["id"], prog)

        print(f"\n=== {w['id']} (cluster={w.get('genre_cluster')}) ===", flush=True)
        result = translate_work(
            w,
            timeout=args.timeout,
            max_output_tokens=args.max_output_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            parallel=args.parallel,
            minimax_model=args.minimax_model,
        )
        prog["events"].append({"ts": utcnow(), "stage": "v2_done", "result": result})
        prog["status"] = "complete" if result.get("exit_code") == 0 else "failed"
        save_progress(w["id"], prog)

        if result.get("exit_code") != 0:
            print(f"  FAILED {w['id']}: {result}", flush=True)
        else:
            print(f"  done {w['id']} in {result['seconds']/60:.1f} min", flush=True)

    overall_elapsed = time.time() - overall_started
    print(f"\n=== v2 corpus pass done in {overall_elapsed/60:.1f} min ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
