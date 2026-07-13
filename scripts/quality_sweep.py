r"""Quality sweep — re-translate the weak public chunks with a stronger engine.

The shipping `public` backend is the best-of-every-backend assembly. Some of
its selected chunks are still weak (adj_faith < 3.2, or flagged hallucinated /
preamble / refusal). This driver re-translates *only* those weak chunks into a
dedicated sweep backend so nothing existing is destroyed:

  - opus  shard -> translations/opus-sweep/full/   (--engine claude-cli, Opus 4.7)
  - codex shard -> translations/codex-sweep/full/   (engine chosen by caller)

`scripts/build_public_backend.py` picks the best graded candidate per chunk
across *all* backends, so a sweep translation only ships if it actually grades
better than what is there now (automatic keep-better — no restore logic).

Work split: cipher / Polygraphiae / Steganographia works (OCR-limited grids
where re-translation has low payoff) go to the codex shard; the prose works
(sermones, de-scriptoribus, de-laudibus, monastic, devotional) go to the
single Opus worker, which is the budgeted lane.

Usage:
    python scripts/quality_sweep.py --shard opus            # launch Opus lane
    python scripts/quality_sweep.py --shard codex            # codex-agent lane
    python scripts/quality_sweep.py --shard opus --dry-run
    python scripts/quality_sweep.py --plan                   # print split, exit
    python scripts/quality_sweep.py --plan --source repo-history
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PUBLIC_SCRIPTS = REPO / "scripts"
MANIFEST = REPO / "manifest.json"

WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
HARNESS = WORKING / "scripts" / "latin_translation_harness.py"
CORPUS = WORKING / "data" / "corpus"
QUALITY = CORPUS / "_quality"
WORKING_PUBLIC_SELECTION = QUALITY / "public_selection.jsonl"
REPO_PUBLIC_SELECTION_HISTORY = REPO / "data" / "_quality" / "public_selection_history.jsonl"
ALLOWLIST_DIR = QUALITY / "sweep_allowlists"
PYTHON_EXE = os.environ.get(
    "TRITHEMIUS_PYTHON",
    r"C:\Users\Ian\AppData\Local\Programs\Python\Python313\python.exe",
)

# Calibration used to decide which selected chunks are "weak".
MM_TO_OPUS_FAITH = {1: 1.70, 2: 2.80, 3: 3.50, 4: 4.40, 5: 4.30}
WEAK_FAITH = 3.2

# Works whose weakness is garbled OCR of cipher grids — re-translation has low
# payoff, so they go to the codex (plan-usage) lane, not the budgeted Opus one.
CIPHER_KEYS = (
    "polygraph", "steganograph", "clavis",
    "spanheimensis-primo-deinde", "veterum-sophorum", "liber-octo",
)


def adj_faith(row: dict) -> float | None:
    v = row.get("faithful")
    if not isinstance(v, int) or not 1 <= v <= 5:
        return None
    if row.get("model") == "claude-opus-4-7":
        return float(v)
    return MM_TO_OPUS_FAITH.get(v, float(v))


def is_weak(row: dict) -> bool:
    af = adj_faith(row)
    return (
        (af is not None and af < WEAK_FAITH)
        or bool(row.get("hallucinated"))
        or bool(row.get("preamble"))
        or bool(row.get("refusal"))
    )


def public_selection_path(source: str) -> Path:
    if source == "repo-history":
        return REPO_PUBLIC_SELECTION_HISTORY
    return WORKING_PUBLIC_SELECTION


def weak_by_work(selection_path: Path) -> dict[str, list[str]]:
    weak: dict[str, list[str]] = defaultdict(list)
    for line in selection_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if is_weak(row):
            rec = (row.get("record") or "").split("/")[-1]
            rec = rec[:-3] if rec.endswith(".md") else rec
            weak[row["work_id"]].append(rec)
    return weak


def split_shards(weak: dict[str, list[str]]) -> tuple[OrderedDict, OrderedDict]:
    opus: OrderedDict[str, list[str]] = OrderedDict()
    codex: OrderedDict[str, list[str]] = OrderedDict()
    for work in sorted(weak, key=lambda w: -len(weak[w])):
        target = codex if any(k in work for k in CIPHER_KEYS) else opus
        target[work] = sorted(set(weak[work]))
    return opus, codex


def cluster_of(work_id: str) -> str | None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for w in data["works"]:
        if w["id"] == work_id:
            return w.get("genre_cluster")
    return None


def run_work(work_id: str, records: list[str], subdir: str, engine: str,
             claude_model: str, dry_run: bool) -> dict:
    cluster = cluster_of(work_id)
    if not cluster:
        return {"work_id": work_id, "skipped": "no cluster"}
    full_txt = CORPUS / work_id / "full.txt"
    if not full_txt.exists():
        return {"work_id": work_id, "skipped": f"missing {full_txt}"}

    ALLOWLIST_DIR.mkdir(parents=True, exist_ok=True)
    allow_path = ALLOWLIST_DIR / f"{subdir}__{work_id}.txt"
    allow_path.write_text("\n".join(records) + "\n", encoding="utf-8")

    cmd = [
        PYTHON_EXE, str(HARNESS), str(full_txt),
        "--engine", engine,
        "--max-output-tokens", "2048",
        "--temperature", "0.2", "--top-p", "0.6",
        "--max-chars", "4500",
        "--out-dir", str(CORPUS / work_id / "translations"),
        "--engine-subdir", subdir,
        "--only-records", str(allow_path),
        "--parallel", "1",
        "--timeout", "900",
        "--use-retrieval", "--use-vulgate", "--ocr-cleanup",
        "--cluster", cluster,
        "--public-repo-scripts", str(PUBLIC_SCRIPTS),
    ]
    if engine == "claude-cli":
        cmd += ["--claude-model", claude_model]

    if dry_run:
        print("DRY:", " ".join(cmd))
        return {"work_id": work_id, "dry": True, "n": len(records)}

    print(f"=== {work_id} ({len(records)} weak, cluster={cluster}) ===", flush=True)
    proc = subprocess.run(cmd, cwd=WORKING)
    return {"work_id": work_id, "exit_code": proc.returncode, "n": len(records)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", choices=["opus", "codex"], help="Which lane to run.")
    ap.add_argument("--plan", action="store_true", help="Print the split and exit.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--engine", default="", help="Override engine (codex lane).")
    ap.add_argument("--claude-model", default="claude-opus-4-7")
    ap.add_argument(
        "--source",
        choices=["working", "repo-history"],
        default="working",
        help="Selection ledger to inspect. working uses the private harness corpus; repo-history uses committed historical data.",
    )
    args = ap.parse_args()

    selection_path = public_selection_path(args.source)
    print(f"selection source: {args.source} ({selection_path})")
    if not selection_path.exists():
        print(f"missing selection ledger: {selection_path}", file=sys.stderr)
        return 1

    weak = weak_by_work(selection_path)
    opus, codex = split_shards(weak)
    n_opus = sum(len(v) for v in opus.values())
    n_codex = sum(len(v) for v in codex.values())
    print(f"weak public chunks: {n_opus + n_codex}")
    print(f"  opus  lane: {n_opus:4d} chunks / {len(opus)} works (prose, budgeted)")
    print(f"  codex lane: {n_codex:4d} chunks / {len(codex)} works (cipher+, plan)")

    if args.plan or not args.shard:
        for name, sh in (("OPUS", opus), ("CODEX", codex)):
            print(f"\n{name}:")
            for w, v in sh.items():
                print(f"  {len(v):3d}  {w}")
        return 0

    if args.shard == "opus":
        works, subdir, engine = opus, "opus-sweep", "claude-cli"
    else:
        works, subdir = codex, "codex-sweep"
        engine = args.engine or "openai"  # codex agent sets its own engine

    results = []
    for work_id, records in works.items():
        results.append(run_work(work_id, records, subdir, engine,
                                 args.claude_model, args.dry_run))
    print("\n=== summary ===")
    for r in results:
        print(f"  {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
