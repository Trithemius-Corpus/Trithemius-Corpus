"""Run targeted repairs for chunks left missing in the public backend.

This wrapper reads data/corpus/_quality/public_retranslate_targets.jsonl,
groups targets by work, and invokes the working corpus translation harness
against the `public` backend. Existing public chunks are skipped by the
harness, so each work run only fills the still-missing slots.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKING = Path(r"E:\trithemius")
CORPUS = WORKING / "data" / "corpus"
TARGETS = CORPUS / "_quality" / "public_retranslate_targets.jsonl"
LOG_DIR = CORPUS / "_quality" / "public_repair_logs"
HARNESS = WORKING / "scripts" / "latin_translation_harness.py"
MANIFEST = REPO / "manifest.json"
PYTHON_EXE = os.environ.get(
    "TRITHEMIUS_PYTHON",
    r"C:\Users\Ian\AppData\Local\Programs\Python\Python313\python.exe",
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def public_file(work_id: str, record: str) -> Path:
    return CORPUS / work_id / "translations" / "public" / "full" / f"{record}.md"


def load_targets() -> dict[str, list[dict]]:
    by_work: dict[str, list[dict]] = defaultdict(list)
    for line in TARGETS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        work_id = row["work_id"]
        record = row["record"]
        path = public_file(work_id, record)
        if path.is_file() and path.stat().st_size > 0:
            continue
        by_work[work_id].append(row)
    return by_work


def cluster_map() -> dict[str, str]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {w["id"]: w.get("genre_cluster") or "" for w in data["works"]}


def run_work(work_id: str, cluster: str, target_count: int, args: argparse.Namespace) -> int:
    full_txt = CORPUS / work_id / "full.txt"
    out_root = CORPUS / work_id / "translations"
    if not full_txt.exists():
        print(f"[skip] no full.txt for {work_id}")
        return 1
    if not cluster:
        print(f"[skip] no genre cluster for {work_id}")
        return 1

    cmd = [
        PYTHON_EXE,
        str(HARNESS),
        str(full_txt),
        "--engine",
        args.engine,
        "--engine-subdir",
        "public",
        "--out-dir",
        str(out_root),
        "--max-output-tokens",
        str(args.max_output_tokens),
        "--temperature",
        str(args.temperature),
        "--top-p",
        str(args.top_p),
        "--max-chars",
        str(args.max_chars),
        "--parallel",
        str(args.parallel),
        "--timeout",
        str(args.timeout),
        "--use-retrieval",
        "--use-vulgate",
        "--ocr-cleanup",
        "--cluster",
        cluster,
        "--public-repo-scripts",
        str(REPO / "scripts"),
        "--quiet-skip-existing",
    ]
    if args.engine == "minimax" and args.refine:
        cmd += ["--refine-on-bad-grade", "--refine-faith-threshold", str(args.refine_faith_threshold)]

    if args.dry_run:
        print("DRY", " ".join(cmd))
        return 0

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{work_id}.log"
    print(f"[work] {work_id} targets={target_count} cluster={cluster}")
    started = time.time()
    interesting = (
        "wrote ",
        "[grade]",
        "[regrade]",
        "[refine]",
        "skip cipher_table",
        "skip steganographia_spirit_list",
        "skip noisy",
        "SKIPPED",
        "FAILED",
        "Traceback",
        "Error",
        "error",
    )
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n\n=== {time.strftime('%Y-%m-%dT%H:%M:%S')} targets={target_count} ===\n")
        log.write(" ".join(cmd) + "\n")
        proc = subprocess.Popen(
            cmd,
            cwd=WORKING,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            if any(token in line for token in interesting):
                print(line.rstrip())
        rc = proc.wait()
        elapsed = round(time.time() - started, 1)
        log.write(f"=== exit={rc} elapsed={elapsed}s ===\n")
    print(f"[done] {work_id} exit={rc} elapsed={elapsed}s log={log_path}")
    return rc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["minimax", "claude-cli"], default="minimax")
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.6)
    parser.add_argument("--max-chars", type=int, default=4500)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--refine", action="store_true", default=True)
    parser.add_argument("--no-refine", action="store_false", dest="refine")
    parser.add_argument("--refine-faith-threshold", type=int, default=3)
    parser.add_argument("--only", default="", help="Only run one work id.")
    parser.add_argument("--max-works", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    targets = load_targets()
    clusters = cluster_map()
    work_ids = sorted(targets)
    if args.only:
        work_ids = [w for w in work_ids if w == args.only]
    if args.max_works:
        work_ids = work_ids[: args.max_works]
    if not work_ids:
        print("No missing public repair targets.")
        return 0

    print(f"repair works={len(work_ids)} chunks={sum(len(targets[w]) for w in work_ids)} engine={args.engine}")
    failures = 0
    for work_id in work_ids:
        failures += 1 if run_work(work_id, clusters.get(work_id, ""), len(targets[work_id]), args) else 0
    print(f"repair complete: failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
