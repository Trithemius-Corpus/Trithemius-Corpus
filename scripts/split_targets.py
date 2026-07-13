"""Split one Vast worker's targets.json into M disjoint sub-lists.

Used by the batched-launch topology: one llama-server per GPU (with --parallel M
+ --cont-batching) is fed by M client worker processes, each with its own
disjoint slice of the page list so no two clients OCR the same page.

Writes targets_0.json ... targets_{M-1}.json next to the input. Each output
keeps the same schema as the input ({"engine","worker_id","pages":[...]}), so
the worker script consumes them unchanged via --targets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def split_pages(pages: list[dict[str, Any]], m: int) -> list[list[dict[str, Any]]]:
    """Round-robin split so work/page are spread evenly across the M slices."""
    shards: list[list[dict[str, Any]]] = [[] for _ in range(m)]
    for i, row in enumerate(pages):
        shards[i % m].append(row)
    return shards


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", type=Path, help="Input targets.json")
    parser.add_argument("--ways", type=int, required=True, help="Number of sub-lists (M clients).")
    parser.add_argument("--suffix", default="", help="Optional stem suffix for output files.")
    args = parser.parse_args()

    data = json.loads(read_text(args.targets))
    pages = data.get("pages")
    if not isinstance(pages, list):
        raise SystemExit("targets JSON must have a 'pages' list")
    if args.ways < 1:
        raise SystemExit("--ways must be >= 1")

    engine = data.get("engine", "qwen3vl-4b-trithemius-q6")
    worker_id = data.get("worker_id", args.targets.stem)
    shards = split_pages(pages, args.ways)

    out_dir = args.targets.parent
    stem = args.targets.stem
    written = []
    for i, shard in enumerate(shards):
        out_path = out_dir / f"{stem}{args.suffix}_{i}.json"
        sub = {"engine": engine, "worker_id": f"{worker_id}_s{i}", "pages": shard}
        write_text(out_path, json.dumps(sub, indent=2, ensure_ascii=False) + "\n")
        written.append((out_path.name, len(shard)))

    total = len(pages)
    print(f"split {total} pages into {args.ways} sub-lists from {args.targets.name}:")
    for name, n in written:
        print(f"  {name}: {n} pages ({100.0 * n / total:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
