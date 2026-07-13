"""Export V3 OCR pages to the Qwen3-VL SFT format used by the OCR trainer."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def to_vlm_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "images": [row["image_path"]],
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
        "source": "v3_ocr",
        "label_source": row["label_method"],
        "quality_flags": row.get("reject_flags") or [],
        "page_type": row["page_type"],
        "image_sha256": row["image_sha256"],
    }


def export(args: argparse.Namespace) -> dict[str, Any]:
    rows = [to_vlm_row(row) for row in read_jsonl(args.input)]
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_split[row["split"]].append(row)

    write_jsonl(args.out / "all.jsonl", rows)
    for split in ("train", "validation", "test"):
        write_jsonl(args.out / f"{split}.jsonl", by_split.get(split, []))

    manifest = {
        "source": args.input.as_posix(),
        "format": "qwen3vl_vlm_sft",
        "counts": {split: len(by_split.get(split, [])) for split in ("train", "validation", "test")},
    }
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "v3" / "v3_ocr_pages.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "v3" / "qwen3vl_ocr_sft")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    manifest = export(parse_args(argv))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
