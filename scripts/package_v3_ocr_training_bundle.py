"""Build a self-contained V3 OCR training bundle for Qwen3-VL.

The package contains resized page images, Qwen3-VL SFT JSONL splits with
relative image paths, the V3 OCR provenance interface, core training/eval
scripts, and a README with exact commands.
"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
Image.MAX_IMAGE_PIXELS = None

OCR_PROMPT = """Transcribe this early-modern printed page faithfully.

Output only the page transcription. Do not translate, summarize, explain, or
describe the image.

Rules:
- Preserve visible line breaks where practical.
- Preserve headings, page numbers, marginal text, cipher strings, tables, and
  non-Latin words exactly as text.
- Normalize long-s to s, but otherwise keep early-modern spelling, v/u and i/j
  choices, punctuation, abbreviations, and capitalization as printed.
- Do not silently expand abbreviations. If a macron or abbreviation mark is
  visible and representable, preserve it; otherwise keep the abbreviated word.
- Use [unclear] for unreadable spans.
- Do not repeat [unclear] line after line. If a larger region is unreadable,
  write [large unreadable section] once and then continue with the next
  readable text.
- Stop after the visible page text. Do not fill blank or unreadable space with
  repeated uncertainty markers.
- If a page is blank or has no meaningful printed text, output [blank page].
"""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def round_to_multiple(value: float, multiple: int = 32) -> int:
    return max(multiple * 2, int(round(value / multiple)) * multiple)


def resized_size(width: int, height: int, max_edge: int) -> tuple[int, int]:
    edge = max(width, height)
    if edge <= max_edge:
        scale = 1.0
    else:
        scale = max_edge / edge
    return round_to_multiple(width * scale), round_to_multiple(height * scale)


def resize_image(src: Path, dst: Path, max_edge: int, quality: int) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 1024:
        try:
            with Image.open(src) as original:
                original_size = original.size
            with Image.open(dst) as existing:
                target_size = existing.size
                existing.verify()
            return {
                "original_width": original_size[0],
                "original_height": original_size[1],
                "width": target_size[0],
                "height": target_size[1],
                "sha256": file_sha256(dst),
                "bytes": dst.stat().st_size,
                "reused": True,
            }
        except Exception:
            dst.unlink(missing_ok=True)
    with Image.open(src) as image:
        image = image.convert("RGB")
        original_size = image.size
        target_size = resized_size(original_size[0], original_size[1], max_edge)
        if image.size != target_size:
            image = image.resize(target_size, Image.Resampling.LANCZOS)
        image.save(dst, format="JPEG", quality=quality, optimize=True)
    return {
        "original_width": original_size[0],
        "original_height": original_size[1],
        "width": target_size[0],
        "height": target_size[1],
        "sha256": file_sha256(dst),
        "bytes": dst.stat().st_size,
        "reused": False,
    }


def to_vlm_row(row: dict[str, Any], image_rel: str) -> dict[str, Any]:
    return {
        "id": row["id"],
        "images": [image_rel],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": OCR_PROMPT},
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": row["label_text"].strip()}],
            },
        ],
        "target": row["label_text"].strip(),
        "split": row["split"],
        "work_id": row["work_id"],
        "page": row["page_id"],
        "source": "v3_ocr_resized_self_contained",
        "label_source": row["label_method"],
        "quality_flags": row.get("reject_flags") or [],
        "page_type": row["page_type"],
        "image_sha256": row["image_sha256"],
        "resized_image_sha256": row["resized_image_sha256"],
    }


def package_one_row(row: dict[str, Any], source_base: Path, out: Path, max_edge: int, jpeg_quality: int) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    split = row["split"]
    src = Path(row["image_path"])
    if not src.is_absolute():
        src = source_base / src
    vlm_image_rel = f"images/{split}/{row['id']}.jpg"
    package_image_rel = f"qwen3vl_ocr_sft/{vlm_image_rel}"
    dst = out / package_image_rel
    stats = resize_image(src, dst, max_edge, jpeg_quality)

    package_row = dict(row)
    package_row["original_image_path"] = row["image_path"]
    package_row["original_image_sha256"] = row["image_sha256"]
    package_row["image_path"] = package_image_rel
    package_row["resized_image_sha256"] = stats["sha256"]
    package_row["image_sha256"] = stats["sha256"]
    package_row["resized_width"] = stats["width"]
    package_row["resized_height"] = stats["height"]
    return split, package_row, to_vlm_row(package_row, vlm_image_rel), stats


def copy_support_files(bundle: Path, *, include_translation_pairs: bool) -> None:
    support_files = [
        ROOT / "scripts" / "train_qwen3vl_ocr_lora_unsloth.py",
        ROOT / "scripts" / "eval_qwen3vl_ocr_lora.py",
        ROOT / "scripts" / "build_v3_datasets.py",
        ROOT / "scripts" / "validate_v3_datasets.py",
        ROOT / "scripts" / "export_v3_ocr_to_qwen_vlm.py",
        ROOT / "scripts" / "package_v3_ocr_training_bundle.py",
        ROOT / "scripts" / "v3_output_guards.py",
        ROOT / "docs" / "V3_DATASET_IMPLEMENTATION.md",
        ROOT / "data" / "v3" / "README.md",
        ROOT / "data" / "v3" / "manifest.json",
        ROOT / "data" / "v3" / "v3_eval_cases.jsonl",
        ROOT / "data" / "v3" / "latin_ocr_confusion_matrix.json",
    ]
    if include_translation_pairs:
        support_files.append(ROOT / "data" / "v3" / "v3_translation_pairs.jsonl")
    for src in support_files:
        if not src.exists():
            continue
        if src.is_relative_to(ROOT / "scripts"):
            rel = Path("scripts") / src.name
        elif src.is_relative_to(ROOT / "docs"):
            rel = Path("docs") / src.name
        elif src.is_relative_to(ROOT / "data" / "v3"):
            rel = Path("v3_metadata") / src.name
        else:
            rel = Path(src.name)
        dst = bundle / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def readme_text(max_edge: int, quality: int) -> str:
    return f"""# Trithemius V3 OCR Training Bundle

Self-contained Qwen3-VL OCR LoRA package.

Image sizing:
- Images are resized client-side to max edge `{max_edge}px`.
- Aspect ratio is preserved.
- Final dimensions are rounded to multiples of 32 for Qwen3-VL.
- JPEG quality is `{quality}`.

Why not 800x600:
- Qwen3-VL accepts variable image sizes.
- Early printed Latin OCR needs glyph-level detail.
- 800x600 is acceptable for smoke tests, but too lossy for this full training package.

Dry run:

```bash
python scripts/train_qwen3vl_ocr_lora_unsloth.py \\
  --dataset-dir qwen3vl_ocr_sft \\
  --output-dir runs/qwen3vl-4b-v3-ocr-dryrun \\
  --dry-run
```

Full 4B run:

```bash
python scripts/train_qwen3vl_ocr_lora_unsloth.py \\
  --dataset-dir qwen3vl_ocr_sft \\
  --output-dir runs/qwen3vl-4b-v3-ocr-500step \\
  --model unsloth/Qwen3-VL-4B-Instruct \\
  --batch-size 1 \\
  --gradient-accumulation-steps 8 \\
  --max-steps 500 \\
  --save-steps 100
```

The 500-step default is about one pass over the 4,416 train examples at the
default effective batch size of 8.
"""


def zip_dir(src_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(src_dir.rglob("*")):
            if path == zip_path:
                continue
            if path.is_file():
                zf.write(path, path.relative_to(src_dir))


def build(args: argparse.Namespace) -> dict[str, Any]:
    source_rows = read_jsonl(args.source)
    if args.clean and args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True, exist_ok=True)

    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    packaged_rows: list[dict[str, Any]] = []
    image_stats: list[dict[str, Any]] = []
    sft_dir = args.out / "qwen3vl_ocr_sft"

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(package_one_row, row, args.source.parent, args.out, args.max_edge, args.jpeg_quality)
            for row in source_rows
        ]
        for idx, future in enumerate(as_completed(futures), 1):
            split, package_row, vlm_row, stats = future.result()
            image_stats.append(stats)
            packaged_rows.append(package_row)
            by_split[split].append(vlm_row)
            if args.progress_every and idx % args.progress_every == 0:
                reused = sum(1 for stat in image_stats if stat.get("reused"))
                print(f"resized {idx}/{len(source_rows)} reused={reused}")

    packaged_rows.sort(key=lambda item: (item["split"], item["work_id"], item["page_id"], item["id"]))
    for split_rows in by_split.values():
        split_rows.sort(key=lambda item: (item["work_id"], item["page"], item["id"]))
    all_vlm_rows = [row for split in ("train", "validation", "test") for row in by_split.get(split, [])]
    write_jsonl(sft_dir / "all.jsonl", all_vlm_rows)
    for split in ("train", "validation", "test"):
        write_jsonl(sft_dir / f"{split}.jsonl", by_split.get(split, []))

    write_jsonl(args.out / "v3_ocr_pages.jsonl", packaged_rows)
    copy_support_files(args.out, include_translation_pairs=args.include_translation_pairs)
    (args.out / "README.md").write_text(readme_text(args.max_edge, args.jpeg_quality), encoding="utf-8")

    counts = {split: len(by_split.get(split, [])) for split in ("train", "validation", "test")}
    total_image_bytes = sum(stat["bytes"] for stat in image_stats)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": args.source.as_posix(),
        "package_name": args.out.name,
        "image_policy": {
            "max_edge": args.max_edge,
            "jpeg_quality": args.jpeg_quality,
            "preserve_aspect_ratio": True,
            "dimension_multiple": 32,
            "rationale": "Qwen3-VL supports variable image sizes; OCR needs more detail than 800x600.",
            "include_translation_pairs": args.include_translation_pairs,
        },
        "counts": counts,
        "page_types": dict(sorted(Counter(row["page_type"] for row in packaged_rows).items())),
        "total_resized_image_bytes": total_image_bytes,
        "total_resized_image_mb": round(total_image_bytes / 1024 / 1024, 2),
        "files": {
            "sft_train": "qwen3vl_ocr_sft/train.jsonl",
            "sft_validation": "qwen3vl_ocr_sft/validation.jsonl",
            "sft_test": "qwen3vl_ocr_sft/test.jsonl",
            "ocr_provenance": "v3_ocr_pages.jsonl",
        },
    }
    write_json(args.out / "package_manifest.json", manifest)

    if args.zip:
        zip_dir(args.out, args.zip)
        manifest["zip_path"] = args.zip.as_posix()
        manifest["zip_sha256"] = file_sha256(args.zip)
        manifest["zip_bytes"] = args.zip.stat().st_size
        write_json(args.out / "package_manifest.json", manifest)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data" / "v3" / "v3_ocr_pages.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / ".cache" / "trithemius_v3_ocr_qwen3vl_1600px_training_bundle")
    parser.add_argument("--zip", type=Path, default=ROOT / ".cache" / "trithemius_v3_ocr_qwen3vl_1600px_training_bundle.zip")
    parser.add_argument("--max-edge", type=int, default=1600)
    parser.add_argument("--jpeg-quality", type=int, default=92)
    parser.add_argument("--progress-every", type=int, default=250)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--include-translation-pairs", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    manifest = build(parse_args(argv))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
