"""Build high-precision Qwen3-VL OCR LoRA training data.

The output is a local VLM SFT dataset in the "images + messages" shape used by
Unsloth vision fine-tuning:

    {
      "images": ["images/example.jpg"],
      "messages": [
        {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "..."}]},
        {"role": "assistant", "content": [{"type": "text", "text": "transcription"}]}
      ],
      ...
    }

Corpus labels are intentionally conservative. Raw OCR witnesses are not treated
as gold unless at least two independent witnesses agree closely, or an explicit
teacher/adjudicated label is supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKING = Path(r"E:\trithemius")
CORPUS = WORKING / "data" / "corpus"

HOLDOUT_WORKS = {
    "prdl-24376_ecloga-de-laude-calvorum-ad-carolum",
    "prdl-24364_de-laudibus-sanctissimae-matris-annae",
    "prdl-24362_de-laude-scriptorum-manualium",
    "prdl-70291_dilibri_veterum-sophorum-sigilla-et-imagines-magicae",
}

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

PAGE_MARK_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.MULTILINE)
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")
TEXT_FIELDS = ("text", "target", "transcription", "ocr", "label", "corrected_text")


@dataclass
class Witness:
    name: str
    text: str
    bad: bool
    flags: list[str]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def split_page_markers(text: str) -> dict[int, str]:
    matches = list(PAGE_MARK_RE.finditer(text))
    pages: dict[int, str] = {}
    for index, match in enumerate(matches):
        page = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        pages[page] = text[start:end].strip()
    return pages


def alpha_count(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def compact_text(text: str) -> str:
    text = PAGE_MARK_RE.sub("", text)
    text = text.replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def similarity(a: str, b: str) -> float:
    aa = compact_text(a)
    bb = compact_text(b)
    if not aa and not bb:
        return 1.0
    if not aa or not bb:
        return 0.0
    return SequenceMatcher(None, aa, bb, autojunk=False).ratio()


def is_blank_text(text: str, min_alpha: int) -> bool:
    lowered = compact_text(text)
    return lowered in {"[blank page]", "blank page", ""} or alpha_count(text) < min_alpha


def repeated_line_loop(text: str) -> bool:
    lines = [compact_text(line) for line in text.splitlines()]
    lines = [line for line in lines if len(line) >= 8 and line not in {"[unclear]", "[blank page]"}]
    if len(lines) < 6:
        return False
    run = 1
    last = None
    for line in lines:
        if line == last:
            run += 1
            if run >= 4:
                return True
        else:
            run = 1
            last = line
    counts = Counter(lines)
    _, count = counts.most_common(1)[0]
    return count >= 6 and count / max(len(lines), 1) >= 0.40


def witness_flags(text: str, min_alpha: int) -> list[str]:
    flags: list[str] = []
    lowered = compact_text(text)
    if not text.strip():
        flags.append("empty")
    if text.lstrip().startswith("[ERROR"):
        flags.append("error_marker")
    if "as an ai" in lowered or "i cannot" in lowered or "i'm sorry" in lowered:
        flags.append("assistant_refusal")
    if repeated_line_loop(text):
        flags.append("repeated_line_loop")
    if is_blank_text(text, min_alpha):
        flags.append("blank_or_tiny")
    return flags


def read_qwen_metrics(qwen_dir: Path) -> dict[int, dict[str, Any]]:
    metrics: dict[int, dict[str, Any]] = {}
    for name in ("qwen3vl_page_metrics.jsonl", "metrics.jsonl"):
        path = qwen_dir / name
        if not path.exists():
            continue
        for line in read_text(path).splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            page = row.get("page")
            if isinstance(page, int):
                metrics[page] = row
    return metrics


def load_teacher_labels(path: Path | None) -> dict[tuple[str, int], str]:
    if path is None or not path.exists():
        return {}
    labels: dict[tuple[str, int], str] = {}
    if path.is_file():
        if path.suffix.lower() == ".json":
            data = json.loads(read_text(path))
            rows = data if isinstance(data, list) else data.get("rows", [])
        else:
            rows = [json.loads(line) for line in read_text(path).splitlines() if line.strip()]
        for row in rows:
            if not isinstance(row, dict):
                continue
            work = row.get("work_id") or row.get("work")
            page = row.get("page")
            text = next((row.get(field) for field in TEXT_FIELDS if row.get(field)), None)
            if isinstance(work, str) and isinstance(page, int) and isinstance(text, str):
                labels[(work, page)] = text.strip()
        return labels

    for text_file in path.rglob("page_*.txt"):
        page_match = re.search(r"page_0*(\d+)", text_file.stem)
        if not page_match:
            continue
        work_parts = [part for part in text_file.parts if part.startswith("prdl-")]
        if not work_parts:
            continue
        labels[(work_parts[-1], int(page_match.group(1)))] = read_text(text_file).strip()
    return labels


def choose_label(
    witnesses: list[Witness],
    *,
    agreement_threshold: float,
    min_alpha: int,
) -> tuple[str | None, str | None, list[str], str | None]:
    hard_bad = [
        flag
        for witness in witnesses
        for flag in witness.flags
        if flag in {"error_marker", "assistant_refusal", "repeated_line_loop", "qwen_capped_or_error"}
    ]
    if hard_bad:
        return None, None, hard_bad, "bad_witness_marker"

    usable = [witness for witness in witnesses if not witness.bad and witness.text.strip()]
    if len(usable) < 2:
        return None, None, ["too_few_witnesses"], "too_few_witnesses"

    blanks = [witness for witness in usable if is_blank_text(witness.text, min_alpha)]
    nonblanks = [witness for witness in usable if not is_blank_text(witness.text, min_alpha)]
    if blanks and nonblanks:
        return None, None, ["blank_disagreement"], "blank_disagreement"
    if blanks and not nonblanks:
        return "[blank page]", "blank_witness_agreement", ["blank_witness_agreement"], None

    pairs: list[tuple[float, Witness, Witness]] = []
    for i, left in enumerate(nonblanks):
        for right in nonblanks[i + 1 :]:
            pairs.append((similarity(left.text, right.text), left, right))
    pairs.sort(key=lambda item: item[0], reverse=True)
    if not pairs or pairs[0][0] < agreement_threshold:
        return None, None, [f"best_similarity={pairs[0][0]:.3f}" if pairs else "no_pairs"], "major_witness_disagreement"

    _, left, right = pairs[0]
    preferred = left
    if right.name == "qwen":
        preferred = right
    if left.name == "qwen":
        preferred = left
    label_source = "_".join(sorted({left.name, right.name})) + "_agreement"
    flags = [label_source, f"agreement={pairs[0][0]:.3f}"]
    return preferred.text.strip(), label_source, flags, None


def stable_split(key: str, *, validation_pct: int, test_pct: int) -> str:
    value = int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16) % 100
    if value < test_pct:
        return "test"
    if value < test_pct + validation_pct:
        return "validation"
    return "train"


def row_id(*parts: str) -> str:
    return hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()[:16]


def make_vlm_row(
    *,
    example_id: str,
    image_rel: str,
    target: str,
    source: str,
    label_source: str,
    split: str,
    quality_flags: list[str],
    work_id: str | None = None,
    page: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": example_id,
        "images": [image_rel.replace("\\", "/")],
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
                "content": [{"type": "text", "text": target.strip()}],
            },
        ],
        "target": target.strip(),
        "work_id": work_id,
        "page": page,
        "source": source,
        "label_source": label_source,
        "quality_flags": quality_flags,
        "split": split,
    }
    if extra:
        row.update(extra)
    return row


def copy_image(src: Path, out_images: Path, name: str, max_edge: int, dry_run: bool) -> str:
    suffix = ".jpg"
    dst = out_images / f"{name}{suffix}"
    rel = Path("images") / dst.name
    if dry_run:
        return rel.as_posix()
    if dst.exists() and dst.stat().st_size > 0:
        return rel.as_posix()
    out_images.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = None
        with Image.open(src) as image:
            image = image.convert("RGB")
            width, height = image.size
            edge = max(width, height)
            if edge > max_edge:
                scale = max_edge / edge
                size = (max(1, int(width * scale)), max(1, int(height * scale)))
                image = image.resize(size, Image.Resampling.LANCZOS)
            image.save(dst, format="JPEG", quality=92, optimize=True)
    except Exception:
        dst = out_images / f"{name}{src.suffix.lower()}"
        rel = Path("images") / dst.name
        shutil.copy2(src, dst)
    return rel.as_posix()


def work_dirs(corpus_root: Path, work_ids: list[str] | None, holdout_only: bool) -> list[Path]:
    dirs = sorted(
        path
        for path in corpus_root.iterdir()
        if path.is_dir() and not path.name.startswith("_") and (path / "pages").is_dir()
    )
    if work_ids:
        wanted = set(work_ids)
        dirs = [path for path in dirs if path.name in wanted]
    if holdout_only:
        dirs = [path for path in dirs if path.name in HOLDOUT_WORKS]
    return dirs


def build_corpus_rows(args: argparse.Namespace, teacher_labels: dict[tuple[str, int], str]) -> tuple[list[dict[str, Any]], Counter]:
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    out_images = args.out / "images"
    qwen_rel = Path(args.qwen_witness_dir)

    for work_dir in work_dirs(args.corpus_root, args.work_id, args.holdout_only):
        work_id = work_dir.name
        qwen_dir = work_dir / qwen_rel
        qwen_metrics = read_qwen_metrics(qwen_dir)
        existing_pages = split_page_markers(read_text(work_dir / "full.txt")) if (work_dir / "full.txt").exists() else {}
        churro_pages = split_page_markers(read_text(work_dir / "churro_full.txt")) if (work_dir / "churro_full.txt").exists() else {}
        images = sorted((work_dir / "pages").glob("page_*.png"))
        for image in images:
            page_match = re.search(r"page_0*(\d+)", image.stem)
            if not page_match:
                continue
            page = int(page_match.group(1))
            if args.max_corpus_pages and len(rows) >= args.max_corpus_pages:
                return rows, rejected

            teacher = teacher_labels.get((work_id, page))
            qwen_text = read_text(qwen_dir / f"page_{page:03d}.txt").strip() if (qwen_dir / f"page_{page:03d}.txt").exists() else ""
            churro_text = churro_pages.get(page, "")
            existing_text = existing_pages.get(page, "")
            metric = qwen_metrics.get(page, {})

            qwen_bad = bool(metric.get("error") or metric.get("capped"))
            witnesses = [
                Witness("qwen", qwen_text, qwen_bad, witness_flags(qwen_text, args.min_alpha) + (["qwen_capped_or_error"] if qwen_bad else [])),
                Witness("churro", churro_text, False, witness_flags(churro_text, args.min_alpha)),
                Witness("existing", existing_text, False, witness_flags(existing_text, args.min_alpha)),
            ]

            if teacher:
                target = teacher
                label_source = "teacher_adjudicated"
                quality_flags = ["teacher_adjudicated"]
            else:
                target, label_source, quality_flags, reason = choose_label(
                    witnesses,
                    agreement_threshold=args.agreement_threshold,
                    min_alpha=args.min_alpha,
                )
                if reason:
                    rejected[reason] += 1
                    continue
                if target is None or label_source is None:
                    rejected["no_label"] += 1
                    continue

            split = "test" if work_id in HOLDOUT_WORKS else stable_split(
                f"trithemius:{work_id}:{page}",
                validation_pct=args.validation_pct,
                test_pct=0,
            )
            if split == "test":
                quality_flags.append("fixed_trithemius_holdout")

            example_id = f"trithemius-{work_id}-p{page:03d}"
            image_rel = copy_image(
                image,
                out_images,
                row_id("trithemius", work_id, str(page)),
                args.image_max_edge,
                args.dry_run,
            )
            rows.append(
                make_vlm_row(
                    example_id=example_id,
                    image_rel=image_rel,
                    target=target,
                    source="trithemius",
                    label_source=label_source,
                    split=split,
                    quality_flags=quality_flags,
                    work_id=work_id,
                    page=page,
                    extra={"witness_dir": str(qwen_rel).replace("\\", "/")},
                )
            )
    return rows, rejected


def paired_gt_text_files(gt_dir: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for text_file in gt_dir.rglob("*.txt"):
        if "__MACOSX" in text_file.parts:
            continue
        if text_file.name.lower().startswith(("readme", "license")):
            continue
        stem = text_file.stem
        if stem.endswith(".gt"):
            stem = stem[:-3]
        candidates = []
        for ext in IMAGE_EXTS:
            candidates.append(text_file.with_name(stem + ext))
            candidates.append(text_file.with_name(text_file.stem + ext))
        image = next((candidate for candidate in candidates if candidate.exists()), None)
        if image:
            pairs.append((image, text_file))
    return sorted(set(pairs))


def build_external_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], Counter]:
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    if not args.gt4histocr_dir:
        return rows, rejected

    out_images = args.out / "images"
    pairs = paired_gt_text_files(args.gt4histocr_dir)
    for image, text_file in pairs:
        if args.max_external_examples and len(rows) >= args.max_external_examples:
            break
        target = read_text(text_file).strip()
        if alpha_count(target) < args.external_min_alpha:
            rejected["external_too_little_text"] += 1
            continue
        key = f"gt4histocr:{image.relative_to(args.gt4histocr_dir)}"
        split = stable_split(key, validation_pct=args.validation_pct, test_pct=args.external_test_pct)
        example_hash = row_id("gt4histocr", str(image))
        image_rel = copy_image(image, out_images, example_hash, args.image_max_edge, args.dry_run)
        rows.append(
            make_vlm_row(
                example_id=f"gt4histocr-{example_hash}",
                image_rel=image_rel,
                target=target,
                source="gt4histocr",
                label_source="external_ground_truth",
                split=split,
                quality_flags=["gt4histocr_cc_by_4_0"],
                extra={
                    "external_image": str(image),
                    "external_text": str(text_file),
                    "license": "CC-BY-4.0",
                },
            )
        )
    return rows, rejected


def summarize(rows: list[dict[str, Any]], rejected: Counter) -> dict[str, Any]:
    by_split = Counter(row["split"] for row in rows)
    by_source = Counter(row["source"] for row in rows)
    by_label = Counter(row["label_source"] for row in rows)
    holdout = Counter(row["work_id"] for row in rows if row.get("work_id") in HOLDOUT_WORKS)
    return {
        "total_examples": len(rows),
        "by_split": dict(sorted(by_split.items())),
        "by_source": dict(sorted(by_source.items())),
        "by_label_source": dict(sorted(by_label.items())),
        "fixed_holdout_examples": dict(sorted(holdout.items())),
        "rejected": dict(sorted(rejected.items())),
    }


def build_dataset(args: argparse.Namespace) -> dict[str, Any]:
    args.out = args.out.resolve()
    args.corpus_root = args.corpus_root.resolve()
    if args.gt4histocr_dir:
        args.gt4histocr_dir = args.gt4histocr_dir.resolve()

    all_rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    teacher_labels = load_teacher_labels(args.teacher_labels)

    if not args.skip_corpus:
        rows, rejects = build_corpus_rows(args, teacher_labels)
        all_rows.extend(rows)
        rejected.update({f"corpus:{key}": value for key, value in rejects.items()})

    rows, rejects = build_external_rows(args)
    all_rows.extend(rows)
    rejected.update({f"gt4histocr:{key}": value for key, value in rejects.items()})

    split_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        split_rows[row["split"]].append(row)

    manifest = {
        "dataset": "qwen3vl_ocr_lora_v0",
        "created_by": Path(__file__).name,
        "corpus_root": str(args.corpus_root),
        "gt4histocr_dir": str(args.gt4histocr_dir) if args.gt4histocr_dir else None,
        "qwen_witness_dir": args.qwen_witness_dir,
        "agreement_threshold": args.agreement_threshold,
        "image_max_edge": args.image_max_edge,
        "holdout_works": sorted(HOLDOUT_WORKS),
        "teacher_label_count": len(teacher_labels),
        "summary": summarize(all_rows, rejected),
    }

    if args.dry_run:
        return manifest

    args.out.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out / "all.jsonl", all_rows)
    for split in ("train", "validation", "test"):
        write_jsonl(args.out / f"{split}.jsonl", split_rows.get(split, []))
    write_json(args.out / "manifest.json", manifest)
    return manifest


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / ".cache" / "qwen3vl-ocr-lora-dataset" / "v0")
    parser.add_argument("--corpus-root", type=Path, default=Path("E:/trithemius/data/corpus"))
    parser.add_argument("--skip-corpus", action="store_true")
    parser.add_argument("--work-id", action="append", help="Limit corpus build to one work id. May be repeated.")
    parser.add_argument("--holdout-only", action="store_true", help="Limit corpus build to the fixed held-out works.")
    parser.add_argument("--qwen-witness-dir", default="translations/_reocr/qwen3vl-4b-instruct-q6")
    parser.add_argument("--teacher-labels", type=Path)
    parser.add_argument("--gt4histocr-dir", type=Path)
    parser.add_argument("--image-max-edge", type=int, default=768)
    parser.add_argument("--agreement-threshold", type=float, default=0.86)
    parser.add_argument("--min-alpha", type=int, default=20)
    parser.add_argument("--external-min-alpha", type=int, default=2)
    parser.add_argument("--validation-pct", type=int, default=5)
    parser.add_argument("--external-test-pct", type=int, default=10)
    parser.add_argument("--max-corpus-pages", type=int)
    parser.add_argument("--max-external-examples", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    manifest = build_dataset(args)
    print(json.dumps(manifest["summary"], ensure_ascii=False, indent=2))
    if args.dry_run:
        print("Dry run only; no dataset files were written.")
    else:
        print(f"Wrote dataset to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
