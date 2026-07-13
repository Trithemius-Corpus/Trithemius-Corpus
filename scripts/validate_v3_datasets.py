"""Validate the V3 OCR and translation dataset interfaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]

OCR_REQUIRED = {
    "id",
    "split",
    "work_id",
    "page_id",
    "page_type",
    "image_path",
    "image_sha256",
    "source_url",
    "license",
    "witnesses",
    "label_text",
    "label_method",
    "label_confidence",
    "reject_flags",
}

TRANSLATION_REQUIRED = {
    "id",
    "split",
    "work_id",
    "chunk_id",
    "input_latin",
    "input_kind",
    "noise_profile",
    "output_english",
    "label_method",
    "grade_provenance",
    "source_weight",
    "tags",
}

EVAL_REQUIRED = {
    "id",
    "task",
    "split",
    "work_id",
    "failure_modes",
    "input_refs",
    "expected_output",
    "gate_group",
}

PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]{1,}")
LATIN_HINTS = {
    "ad",
    "autem",
    "cum",
    "de",
    "dominus",
    "enim",
    "esse",
    "est",
    "et",
    "haec",
    "hoc",
    "illa",
    "in",
    "ipse",
    "non",
    "per",
    "quae",
    "qui",
    "quod",
    "quo",
    "quos",
    "sua",
    "sunt",
    "suo",
    "ut",
}
ENGLISH_HINTS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "but",
    "by",
    "even",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "into",
    "is",
    "it",
    "my",
    "not",
    "of",
    "or",
    "shall",
    "so",
    "than",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "which",
    "with",
    "you",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def words(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text or "")]


def looks_latin(text: str) -> bool:
    toks = words(text)
    if len(toks) < 4:
        return False
    return sum(1 for token in toks[:250] if token in LATIN_HINTS or token.endswith(("um", "us", "ae", "is", "ibus"))) >= 2


def looks_english(text: str) -> bool:
    toks = words(text)
    if len(toks) < 4:
        return False
    hits = sum(1 for token in toks[:250] if token in ENGLISH_HINTS)
    return hits >= 1 if len(toks) < 12 else hits >= 2


def alpha_count(text: str) -> int:
    return sum(1 for char in (text or "") if char.isalpha())


def length_ratio_ok(latin: str, english: str) -> bool:
    ratio = len(english or "") / max(1, len(latin or ""))
    return alpha_count(latin) >= 20 and alpha_count(english) >= 20 and 0.20 <= ratio <= 4.00


def require_fields(rows: Iterable[dict[str, Any]], fields: set[str], label: str, errors: list[str]) -> None:
    for row in rows:
        missing = sorted(field for field in fields if field not in row)
        if missing:
            errors.append(f"{label}:{row.get('_line_no')}: missing fields {missing}")


def check_unique(rows: Iterable[dict[str, Any]], label: str, errors: list[str]) -> None:
    counts = Counter(str(row.get("id")) for row in rows)
    for row_id, count in counts.items():
        if count > 1:
            errors.append(f"{label}: duplicate id {row_id} x{count}")


def check_split_leakage(rows: Iterable[dict[str, Any]], label: str, errors: list[str]) -> None:
    by_work: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        by_work[str(row.get("work_id"))].add(str(row.get("split")))
    for work_id, splits in by_work.items():
        if len(splits) > 1:
            errors.append(f"{label}: work/source family {work_id} appears in multiple splits {sorted(splits)}")


def validate_ocr(rows: list[dict[str, Any]], errors: list[str], warnings: list[str]) -> None:
    require_fields(rows, OCR_REQUIRED, "ocr", errors)
    check_unique(rows, "ocr", errors)
    check_split_leakage(rows, "ocr", errors)
    by_split = Counter(str(row.get("split")) for row in rows)
    for split in ("train", "validation", "test"):
        if by_split.get(split, 0) == 0:
            warnings.append(f"ocr: no rows in split {split}")

    for row in rows:
        line = row.get("_line_no")
        split = row.get("split")
        if split not in {"train", "validation", "test"}:
            errors.append(f"ocr:{line}: invalid split {split}")
        image_path = Path(str(row.get("image_path") or ""))
        if not image_path.exists():
            errors.append(f"ocr:{line}: image_path missing {image_path}")
        elif sha256_file(image_path) != row.get("image_sha256"):
            errors.append(f"ocr:{line}: image_sha256 mismatch {image_path}")
        if split == "train":
            if not row.get("license"):
                errors.append(f"ocr:{line}: train row missing license")
            if not row.get("source_url"):
                errors.append(f"ocr:{line}: train row missing source_url")
            if not row.get("witnesses"):
                errors.append(f"ocr:{line}: train row missing witnesses")
        if any(str(flag).endswith("_quarantine") for flag in row.get("reject_flags") or []):
            errors.append(f"ocr:{line}: quarantine flag admitted into dataset")


def validate_translation(rows: list[dict[str, Any]], errors: list[str], warnings: list[str]) -> None:
    require_fields(rows, TRANSLATION_REQUIRED, "translation", errors)
    check_unique(rows, "translation", errors)
    check_split_leakage(rows, "translation", errors)
    by_split = Counter(str(row.get("split")) for row in rows)
    for split in ("train", "validation", "test"):
        if by_split.get(split, 0) == 0:
            warnings.append(f"translation: no rows in split {split}")

    for row in rows:
        line = row.get("_line_no")
        split = row.get("split")
        if split not in {"train", "validation", "test"}:
            errors.append(f"translation:{line}: invalid split {split}")
        latin = str(row.get("input_latin") or "")
        english = str(row.get("output_english") or "")
        if "vulgate" in str(row.get("work_id", "")).lower() or "vulgate" in " ".join(map(str, row.get("tags") or [])).lower():
            errors.append(f"translation:{line}: Vulgate row admitted before reference alignment repair")
        if not length_ratio_ok(latin, english):
            errors.append(f"translation:{line}: length/language ratio outlier")
        tags = {str(tag) for tag in row.get("tags") or []}
        requires_prose_language = bool(tags & {"external", "classical_latin", "benedictine", "anchor"})
        if requires_prose_language and not looks_latin(latin):
            errors.append(f"translation:{line}: input_latin language check failed")
        if requires_prose_language and not looks_english(english):
            errors.append(f"translation:{line}: output_english language check failed")
        provenance = row.get("grade_provenance")
        if split == "train":
            if not isinstance(provenance, dict) or not provenance:
                errors.append(f"translation:{line}: train row missing grade_provenance")
            elif not any(key in provenance for key in ("source_file", "external_source", "translation_path", "latin_source_url")):
                errors.append(f"translation:{line}: train row provenance lacks source reference")
        if row.get("input_kind") == "synthetic_ocr_confusion_variant" and row.get("noise_profile") == "clean":
            errors.append(f"translation:{line}: synthetic noise row has clean profile")


def validate_eval(rows: list[dict[str, Any]], errors: list[str], warnings: list[str]) -> None:
    require_fields(rows, EVAL_REQUIRED, "eval", errors)
    check_unique(rows, "eval", errors)
    tasks = Counter(str(row.get("task")) for row in rows)
    if tasks.get("ocr", 0) == 0:
        warnings.append("eval: no OCR eval cases")
    if tasks.get("translation", 0) == 0:
        warnings.append("eval: no translation eval cases")
    for row in rows:
        line = row.get("_line_no")
        if row.get("task") not in {"ocr", "translation"}:
            errors.append(f"eval:{line}: invalid task {row.get('task')}")
        if row.get("split") not in {"validation", "test"}:
            errors.append(f"eval:{line}: eval split must be validation or test")
        if not row.get("failure_modes"):
            errors.append(f"eval:{line}: missing failure_modes")
        if not row.get("input_refs"):
            errors.append(f"eval:{line}: missing input_refs")
        if row.get("expected_output") in (None, ""):
            errors.append(f"eval:{line}: missing expected_output")


def validate(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    ocr = read_jsonl(root / "v3_ocr_pages.jsonl")
    translation = read_jsonl(root / "v3_translation_pairs.jsonl")
    eval_cases = read_jsonl(root / "v3_eval_cases.jsonl")

    errors: list[str] = []
    warnings: list[str] = []
    validate_ocr(ocr, errors, warnings)
    validate_translation(translation, errors, warnings)
    validate_eval(eval_cases, errors, warnings)

    summary = {
        "ocr_rows": len(ocr),
        "ocr_by_split": dict(sorted(Counter(row.get("split") for row in ocr).items())),
        "translation_rows": len(translation),
        "translation_by_split": dict(sorted(Counter(row.get("split") for row in translation).items())),
        "eval_rows": len(eval_cases),
        "eval_by_task": dict(sorted(Counter(row.get("task") for row in eval_cases).items())),
        "errors": len(errors),
        "warnings": len(warnings),
    }
    return errors, warnings, summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "data" / "v3")
    parser.add_argument("--warnings-as-errors", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors, warnings, summary = validate(args.root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors or (warnings and args.warnings_as_errors):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
