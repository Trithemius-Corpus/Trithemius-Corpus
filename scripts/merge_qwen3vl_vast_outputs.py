"""Merge returned Vast OCR shard outputs into the Trithemius working corpus."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"
DEFAULT_ENGINE = "qwen3vl-4b-trithemius-q6"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def page_num(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def page_files(work_id: str) -> list[Path]:
    return sorted((CORPUS / work_id / "pages").glob("page_*.png"))


def dest_root(work_id: str, engine: str) -> Path:
    return CORPUS / work_id / "translations" / "_reocr" / engine


def is_done(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0 and not read_text(path).startswith("[ERROR")


def find_engine_roots(paths: list[Path], engine: str) -> list[Path]:
    roots: list[Path] = []
    for path in paths:
        candidates = [
            path / "ocr_outputs" / engine,
            path / engine,
            path,
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir() and candidate.name == engine:
                roots.append(candidate)
                break
        else:
            roots.extend(found for found in path.rglob(engine) if found.is_dir())
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(roots))


def iter_page_outputs(engine_root: Path) -> list[Path]:
    outputs: list[Path] = []
    for work_dir in engine_root.iterdir():
        if not work_dir.is_dir() or work_dir.name.startswith("_"):
            continue
        outputs.extend(sorted(work_dir.glob("page_*.txt")))
    return outputs


def stitch_full(work_id: str, engine: str) -> Path | None:
    pages = page_files(work_id)
    if not pages:
        return None
    root = dest_root(work_id, engine)
    if not all(is_done(root / f"page_{page_num(image):03d}.txt") for image in pages):
        return None
    lines: list[str] = []
    for image in pages:
        num = page_num(image)
        text = read_text(root / f"page_{num:03d}.txt").strip()
        lines.extend([f"--- Page {num:03d} ---", "", text, ""])
    full = root / "full.txt"
    write_text(full, "\n".join(lines).rstrip() + "\n")
    return full


def load_metrics(engine_roots: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root in engine_roots:
        for path in sorted(root.glob("metrics_*.jsonl")):
            for line in read_text(path).splitlines():
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="+", type=Path, help="Returned worker folder(s) or parent folder.")
    parser.add_argument("--engine", default=DEFAULT_ENGINE)
    parser.add_argument("--no-stitch", action="store_true")
    parser.add_argument("--force", action="store_true", help="Overwrite existing page outputs.")
    args = parser.parse_args()

    engine_roots = find_engine_roots(args.input, args.engine)
    if not engine_roots:
        raise SystemExit(f"No returned ocr_outputs/{args.engine} roots found.")

    copied = skipped = 0
    touched_works: set[str] = set()
    for engine_root in engine_roots:
        for page in iter_page_outputs(engine_root):
            work_id = page.parent.name
            dest = dest_root(work_id, args.engine) / page.name
            if dest.exists() and not args.force:
                skipped += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(page, dest)
            copied += 1
            touched_works.add(work_id)

    metrics_by_work: dict[str, list[dict[str, Any]]] = {}
    for row in load_metrics(engine_roots):
        work = row.get("work")
        if isinstance(work, str):
            metrics_by_work.setdefault(work, []).append(row)
    for work_id, rows in metrics_by_work.items():
        metrics_path = dest_root(work_id, args.engine) / "qwen3vl_page_metrics.jsonl"
        with metrics_path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    stitched: list[str] = []
    incomplete: dict[str, dict[str, int]] = {}
    for work_id in sorted(touched_works | set(metrics_by_work)):
        total = len(page_files(work_id))
        done = sum(1 for image in page_files(work_id) if is_done(dest_root(work_id, args.engine) / f"page_{page_num(image):03d}.txt"))
        if not args.no_stitch:
            full = stitch_full(work_id, args.engine)
            if full:
                stitched.append(str(full))
            else:
                incomplete[work_id] = {"done": done, "total": total}

    report = {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "engine": args.engine,
        "engine_roots": [str(path) for path in engine_roots],
        "copied_pages": copied,
        "skipped_existing_pages": skipped,
        "metrics_rows": sum(len(rows) for rows in metrics_by_work.values()),
        "stitched_full_txt": stitched,
        "incomplete": incomplete,
    }
    report_path = ROOT / ".cache" / "qwen3vl-vast-reocr" / f"merge-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    write_text(report_path, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
