"""Build Vast worker shards for a Trithemius Qwen3-VL re-OCR pass.

By default this writes lightweight shard configs. Pass `--make-zips` to create
per-worker zip payloads containing only that worker's page images plus the
standalone worker script. GGUF model files are intentionally excluded.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import zipfile
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


def prdl_number(work_id: str) -> str | None:
    prefix = work_id.split("_", 1)[0]
    if prefix.startswith("prdl-"):
        return prefix.removeprefix("prdl-")
    return None


def skipped_prdl_numbers() -> set[str]:
    manifest = ROOT / "manifest.json"
    if not manifest.exists():
        return set()
    data = json.loads(read_text(manifest))
    skipped: set[str] = set()
    for work in data.get("works", []):
        if not work.get("skip"):
            continue
        source = work.get("source") if isinstance(work.get("source"), dict) else {}
        prdl_id = source.get("prdl_id")
        if prdl_id:
            skipped.add(str(prdl_id))
        work_id = work.get("id")
        if isinstance(work_id, str):
            number = prdl_number(work_id)
            if number:
                skipped.add(number)
    return skipped


def page_num(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def page_files(work_dir: Path) -> list[Path]:
    return sorted((work_dir / "pages").glob("page_*.png"))


def is_done(page_txt: Path) -> bool:
    return page_txt.exists() and page_txt.stat().st_size > 0 and not read_text(page_txt).startswith("[ERROR")


def selected_works(args: argparse.Namespace) -> list[str]:
    requested = set(args.work or [])
    skipped = skipped_prdl_numbers()
    rows: list[tuple[int, str]] = []
    for work_dir in sorted(CORPUS.iterdir()):
        if not work_dir.is_dir() or work_dir.name.startswith("_"):
            continue
        pages = page_files(work_dir)
        if not pages:
            continue
        number = prdl_number(work_dir.name)
        if number and number in skipped and work_dir.name not in requested and not args.include_skipped:
            continue
        if requested and work_dir.name not in requested:
            continue
        rows.append((len(pages), work_dir.name))
    rows.sort()
    if args.limit:
        rows = rows[: args.limit]
    return [work_id for _, work_id in rows]


def prepare_image(image: Path, out: Path, args: argparse.Namespace) -> Path:
    if not args.prepare_images:
        return image
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    page = page_num(image)
    prepared = out / "staged_pages" / image.parent.parent.name / f"page_{page:03d}.jpg"
    if prepared.exists() and prepared.stat().st_size > 0:
        return prepared
    prepared.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image) as opened:
        opened.thumbnail((args.image_max_edge, args.image_max_edge), Image.Resampling.LANCZOS)
        if opened.mode not in {"RGB", "L"}:
            opened = opened.convert("RGB")
        opened.save(prepared, format="JPEG", quality=args.jpeg_quality, optimize=True)
    return prepared


def collect_tasks(args: argparse.Namespace, out: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for work_id in selected_works(args):
        out_root = CORPUS / work_id / "translations" / "_reocr" / args.engine
        for image in page_files(CORPUS / work_id):
            num = page_num(image)
            if args.pending_only and is_done(out_root / f"page_{num:03d}.txt"):
                continue
            payload_image = prepare_image(image, out, args)
            tasks.append(
                {
                    "work": work_id,
                    "page": num,
                    "image": f"pages/{work_id}/page_{num:03d}{payload_image.suffix.lower()}",
                    "source_image": str(image),
                    "payload_image": str(payload_image),
                    "raw_bytes": image.stat().st_size,
                    "bytes": payload_image.stat().st_size,
                }
            )
    return tasks


def split_tasks(tasks: list[dict[str, Any]], workers: int) -> list[list[dict[str, Any]]]:
    shards: list[list[dict[str, Any]]] = [[] for _ in range(workers)]
    totals = [0 for _ in range(workers)]
    for task in sorted(tasks, key=lambda row: row["bytes"], reverse=True):
        index = min(range(workers), key=lambda i: totals[i])
        shards[index].append(task)
        totals[index] += int(task["bytes"])
    for shard in shards:
        shard.sort(key=lambda row: (row["work"], row["page"]))
    return shards


def target_json(engine: str, worker_id: str, shard: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "engine": engine,
        "worker_id": worker_id,
        "pages": [
            {"work": row["work"], "page": row["page"], "image": row["image"]}
            for row in shard
        ],
    }


def worker_readme(engine: str) -> str:
    return f"""# Trithemius Qwen3-VL Vast Worker

Place the trained Q6 model and F16 mmproj on the worker, then run:

```bash
python scripts/qwen3vl_vast_worker.py \\
  --targets targets.json \\
  --engine {engine} \\
  --model /workspace/models/Qwen3-VL-4B-Trithemius-Q6_K.gguf \\
  --mmproj /workspace/models/mmproj-Qwen3-VL-4B-Trithemius-F16.gguf \\
  --no-mmproj-offload \\
  --ctx-size 8192 \\
  --image-tokens 1024 \\
  --max-tokens 3000 \\
  --worker-id $WORKER_ID
```

Return the `ocr_outputs/` directory from each worker. Merge locally with
`scripts/merge_qwen3vl_vast_outputs.py`.
"""


def make_zip(path: Path, target: dict[str, Any], shard: list[dict[str, Any]], engine: str) -> None:
    worker_script = ROOT / "scripts" / "qwen3vl_vast_worker.py"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.writestr("targets.json", json.dumps(target, indent=2, ensure_ascii=False) + "\n")
        zf.writestr("README_VAST_WORKER.md", worker_readme(engine))
        zf.write(worker_script, "scripts/qwen3vl_vast_worker.py")
        for row in shard:
            zf.write(Path(row["payload_image"]), row["image"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--engine", default=DEFAULT_ENGINE)
    parser.add_argument("--work", action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-skipped", action="store_true")
    parser.add_argument("--pending-only", action="store_true")
    parser.add_argument("--prepare-images", action="store_true", help="Stage resized JPEG payload images.")
    parser.add_argument("--image-max-edge", type=int, default=2400)
    parser.add_argument("--jpeg-quality", type=int, default=92)
    parser.add_argument("--make-zips", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.out or ROOT / ".cache" / "qwen3vl-vast-reocr" / stamp
    out.mkdir(parents=True, exist_ok=True)

    tasks = collect_tasks(args, out)
    shards = split_tasks(tasks, args.workers)
    worker_rows = []
    total_bytes = sum(int(row["bytes"]) for row in tasks)
    raw_bytes = sum(int(row["raw_bytes"]) for row in tasks)
    for index, shard in enumerate(shards):
        worker_id = f"worker_{index:02d}"
        target = target_json(args.engine, worker_id, shard)
        target_path = out / "configs" / f"{worker_id}.json"
        write_text(target_path, json.dumps(target, indent=2, ensure_ascii=False) + "\n")
        zip_path = out / f"{worker_id}.zip"
        if args.make_zips:
            make_zip(zip_path, target, shard, args.engine)
        worker_rows.append(
            {
                "worker_id": worker_id,
                "pages": len(shard),
                "bytes": sum(int(row["bytes"]) for row in shard),
                "target_json": str(target_path),
                "zip": str(zip_path) if args.make_zips else None,
                "command": (
                    "python scripts/qwen3vl_vast_worker.py "
                    f"--targets targets.json --engine {args.engine} "
                    "--model /workspace/models/Qwen3-VL-4B-Trithemius-Q6_K.gguf "
                    "--mmproj /workspace/models/mmproj-Qwen3-VL-4B-Trithemius-F16.gguf "
                    "--no-mmproj-offload --ctx-size 8192 --image-tokens 1024 "
                    "--max-tokens 3000 --worker-id " + worker_id
                ),
            }
        )

    manifest = {
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "engine": args.engine,
        "workers": args.workers,
        "pages": len(tasks),
        "works": len({row["work"] for row in tasks}),
        "raw_image_bytes": raw_bytes,
        "raw_image_gib": round(raw_bytes / 1024 / 1024 / 1024, 3),
        "payload_image_bytes": total_bytes,
        "payload_image_gib": round(total_bytes / 1024 / 1024 / 1024, 3),
        "prepare_images": args.prepare_images,
        "image_max_edge": args.image_max_edge if args.prepare_images else None,
        "jpeg_quality": args.jpeg_quality if args.prepare_images else None,
        "pending_only": args.pending_only,
        "make_zips": args.make_zips,
        "workers_detail": worker_rows,
    }
    manifest_path = out / "manifest.json"
    write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
