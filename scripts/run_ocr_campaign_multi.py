"""Run multiple Qwen3-VL OCR servers over disjoint Trithemius works.

This is the multi-server companion to run_ocr_campaign.py. It builds a
page-level backlog, partitions works across workers, and starts one
qwen3vl_ocr_batch.py process per worker on a fixed localhost port.

Each worker keeps its own llama-server loaded while processing its assigned
works. The underlying batcher remains responsible for page-level resume and
full.txt stitching.
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
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
OCR_SCRIPT = ROOT / "scripts" / "qwen3vl_ocr_batch.py"
CORPUS = Path(r"E:\trithemius\data\corpus")
MANIFEST = ROOT / "manifest.json"
CACHE = ROOT / ".cache" / "qwen3vl-multi-ocr"

ENGINE = "qwen3vl-4b-trithemius-q6"
MODEL = Path(r"E:\trithemius\models\Qwen3-VL-4B-Trithemius-Q6_K.gguf")
MMPROJ = Path(r"E:\trithemius\models\mmproj-Qwen3-VL-4B-Trithemius-F16.gguf")
PROMPT = ROOT / "data" / "prompts" / "qwen3vl_trithemius_ocr_only.txt"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def page_num(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def is_done(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        return not path.read_text(encoding="utf-8", errors="replace").startswith("[ERROR")
    except OSError:
        return False


def manifest_work_ids() -> list[str]:
    manifest = read_json(MANIFEST)
    return [row["id"] for row in manifest.get("works", []) if isinstance(row.get("id"), str)]


def missing_pages(work_id: str, engine: str) -> list[int]:
    pages_dir = CORPUS / work_id / "pages"
    if not pages_dir.is_dir():
        return []
    out_dir = CORPUS / work_id / "translations" / "_reocr" / engine
    missing: list[int] = []
    for image in sorted(pages_dir.glob("page_*.png")):
        num = page_num(image)
        if not is_done(out_dir / f"page_{num:03d}.txt"):
            missing.append(num)
    return missing


def build_backlog(engine: str, requested: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for work_id in manifest_work_ids():
        if requested and work_id not in requested:
            continue
        miss = missing_pages(work_id, engine)
        if not miss:
            continue
        pages_dir = CORPUS / work_id / "pages"
        total_pages = len(list(pages_dir.glob("page_*.png"))) if pages_dir.is_dir() else 0
        rows.append(
            {
                "work": work_id,
                "missing_count": len(miss),
                "missing_first": miss[0],
                "missing_last": miss[-1],
                "pages": total_pages,
            }
        )
    return sorted(rows, key=lambda row: (row["missing_count"], row["work"]))


def partition(backlog: list[dict[str, Any]], workers: int) -> list[dict[str, Any]]:
    shards = [{"worker": i, "pages": 0, "works": []} for i in range(workers)]
    # Keep quick wins first, but assign each next work to the lightest shard.
    for row in backlog:
        shard = min(shards, key=lambda s: (s["pages"], s["worker"]))
        shard["works"].append(row)
        shard["pages"] += row["missing_count"]
    return shards


def command_for_shard(shard: dict[str, Any], args: argparse.Namespace) -> list[str]:
    cmd = [
        PYTHON,
        str(OCR_SCRIPT),
        "--engine",
        args.engine,
        "--max-tokens",
        str(args.max_tokens),
        "--ctx-size",
        str(args.ctx_size),
        "--parallel",
        str(args.parallel),
        "--image-tokens",
        str(args.image_tokens),
        "--split-parts",
        str(args.split_parts),
        "--page-timeout",
        str(args.page_timeout),
        "--model",
        str(args.model),
        "--mmproj",
        str(args.mmproj),
        "--prompt-file",
        str(args.prompt_file),
        "--extract-ocr-section",
        "--port",
        str(args.base_port + shard["worker"]),
    ]
    if args.no_mmproj_offload:
        cmd.append("--no-mmproj-offload")
    for row in shard["works"]:
        cmd.extend(["--work", row["work"]])
    return cmd


def print_plan(shards: list[dict[str, Any]]) -> None:
    total_pages = sum(shard["pages"] for shard in shards)
    total_works = sum(len(shard["works"]) for shard in shards)
    print(f"Plan: {len(shards)} workers, {total_works} works, {total_pages} missing pages")
    for shard in shards:
        first = shard["works"][0]["work"] if shard["works"] else "-"
        print(
            f"  worker {shard['worker']:02d}: "
            f"{len(shard['works']):2d} works, {shard['pages']:4d} pages, first={first}"
        )


def launch(shards: list[dict[str, Any]], args: argparse.Namespace) -> int:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = CACHE / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    plan_path = run_dir / "plan.json"
    write_json(
        plan_path,
        {
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "engine": args.engine,
            "workers": args.workers,
            "base_port": args.base_port,
            "shards": shards,
        },
    )
    print(f"Plan written: {plan_path}")

    procs: list[tuple[int, subprocess.Popen[bytes], Any, Any]] = []
    for shard in shards:
        if not shard["works"]:
            continue
        out_path = run_dir / f"worker_{shard['worker']:02d}.out.log"
        err_path = run_dir / f"worker_{shard['worker']:02d}.err.log"
        cmd_path = run_dir / f"worker_{shard['worker']:02d}.command.txt"
        cmd = command_for_shard(shard, args)
        cmd_path.write_text(subprocess.list2cmdline(cmd), encoding="utf-8")
        out_handle = out_path.open("wb")
        err_handle = err_path.open("wb")
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=out_handle,
            stderr=err_handle,
        )
        procs.append((shard["worker"], proc, out_handle, err_handle))
        print(
            f"started worker {shard['worker']:02d} pid={proc.pid} "
            f"port={args.base_port + shard['worker']} log={out_path}"
        )

    exit_rows: list[dict[str, Any]] = []
    try:
        while procs:
            still_running: list[tuple[int, subprocess.Popen[bytes], Any, Any]] = []
            for worker, proc, out_handle, err_handle in procs:
                rc = proc.poll()
                if rc is None:
                    still_running.append((worker, proc, out_handle, err_handle))
                    continue
                out_handle.close()
                err_handle.close()
                exit_rows.append(
                    {
                        "worker": worker,
                        "pid": proc.pid,
                        "returncode": rc,
                        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    }
                )
                print(f"worker {worker:02d} exited rc={rc}")
            procs = still_running
            if procs:
                time.sleep(args.poll_seconds)
    finally:
        for worker, proc, out_handle, err_handle in procs:
            if proc.poll() is None:
                proc.terminate()
            out_handle.close()
            err_handle.close()
    write_json(run_dir / "exits.json", exit_rows)
    return 0 if all(row["returncode"] == 0 for row in exit_rows) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", default=ENGINE)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--base-port", type=int, default=8091)
    parser.add_argument("--max-works", type=int, default=0)
    parser.add_argument("--work", action="append", help="Restrict to selected work id; repeatable.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ctx-size", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=3000)
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--image-tokens", type=int, default=1024)
    parser.add_argument("--split-parts", type=int, default=1)
    parser.add_argument("--page-timeout", type=int, default=900)
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--mmproj", type=Path, default=MMPROJ)
    parser.add_argument("--prompt-file", type=Path, default=PROMPT)
    parser.add_argument("--no-mmproj-offload", action="store_true", default=True)
    parser.add_argument("--poll-seconds", type=int, default=15)
    args = parser.parse_args()

    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")

    backlog = build_backlog(args.engine, set(args.work or []))
    if args.max_works:
        backlog = backlog[: args.max_works]
    if not backlog:
        print("Nothing to OCR. Backlog is empty.")
        return 0

    shards = partition(backlog, args.workers)
    print_plan(shards)
    if args.dry_run:
        for shard in shards:
            print(f"\nworker {shard['worker']:02d}")
            for row in shard["works"][:20]:
                print(
                    f"  {row['missing_count']:4d} missing "
                    f"{row['missing_first']:03d}-{row['missing_last']:03d} {row['work']}"
                )
        return 0
    return launch(shards, args)


if __name__ == "__main__":
    raise SystemExit(main())
