"""Retranslate a work using Qwen3-VL OCR plus existing corpus context.

For each chunk of the new Qwen3 OCR, the translator receives:
1. Primary witness: Qwen3-VL-Instruct OCR.
2. Secondary witness: current working-corpus OCR for the same source pages.
3. Prior English: existing public translation chunk when available, context only.

Outputs:
    E:/trithemius/data/corpus/<work>/translations/qwen3vl-dual-gpt55/full/
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"
HARNESS = WORKING / "scripts"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

from latin_translation_harness import records_from_file  # type: ignore  # noqa: E402
from v3_output_guards import validate_translation_output  # noqa: E402


CODEX = shutil.which("codex") or r"C:\Users\Ian\AppData\Roaming\npm\codex.cmd"
DEFAULT_MODEL = "gpt-5.5"
NEW_ENGINE = "qwen3vl-4b-instruct-q6"
OUT_BACKEND = "qwen3vl-dual-gpt55"
CHUNK_MAX = 4500

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["english"],
    "properties": {"english": {"type": "string"}},
}

PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)
OUTPUT_PAGE_RE = re.compile(
    r"^(?:---\s*Page\s+0*(\d+)\s*---|\[(?:Page|PAGE)\s+0*(\d+)\])",
    re.M,
)
MOJIBAKE_RE = re.compile(r"[\u00c3\u00c5\u00e2\ufffd]")
CHAPTER_RE = re.compile(
    r"\b(?:cap(?:ut|itulo)?|chap(?:ter)?|cap\.)\s*\.?\s*([ivxlcdm]+|\d+)\b",
    re.I,
)
ARABIC_YEAR_RE = re.compile(r"\b(1[34-6]\d{2})\b")
ROMAN_YEAR_RE = re.compile(
    r"\bm[\s.]*c[\s.]*c[\s.]*c[\s.]*c(?:[\s.]*[cxlvij]+){0,5}\b",
    re.I,
)
COMMON_MOJIBAKE = {
    "\u00e2\u20ac\u0153": '"',
    "\u00e2\u20ac\u009d": '"',
    "\u00e2\u20ac\u02dc": "'",
    "\u00e2\u20ac\u2122": "'",
    "\u00e2\u20ac\u201c": "-",
    "\u00e2\u20ac\u201d": "--",
}

PROMPT_TEMPLATE = """You are translating Johannes Trithemius-related early printed Latin into faithful, clear scholarly English.

You have three context layers:

1. PRIMARY OCR WITNESS: a fresh Qwen3-VL-Instruct transcription from page images.
2. SECONDARY OCR WITNESS: the existing working-corpus OCR for the same source page span.
3. PRIOR ENGLISH: the previous corpus translation, supplied only to avoid regressions.

Translation rules:
- Translate the Latin source, not the prior English.
- Prefer the primary OCR where it is clearly legible, but use the secondary OCR to correct obvious OCR confusions.
- If the primary OCR is garbled but the secondary OCR gives a clear Latin reading, translate from the secondary and do not mark [unclear].
- Use [unclear] only when both OCR witnesses are corrupt, materially ambiguous, or require image inspection.
- If both witnesses show a likely printer or OCR oddity, translate the best-supported reading without hiding ordinary grammar behind [unclear].
- Never invent content to fill gaps.
- Preserve names, dates, book/chapter references, rubrics, and page markers.
- If the passage is a table, acrostic, cipher text, catalogue, or verse, preserve its structure as much as English allows.
- If a primary page says it was flagged by Qwen3-VL OCR, translate that page from the secondary OCR witness and keep the page marker.
- Output only the English translation through the JSON schema. No commentary.

--- SOURCE PAGES ---
{pages}

--- PRIMARY OCR WITNESS: Qwen3-VL-Instruct ---
{primary}

--- SECONDARY OCR WITNESS: existing corpus OCR ---
{secondary}

--- PRIOR ENGLISH CONTEXT ONLY ---
{prior}
"""

PLACEHOLDER = (
    "[Source illegible or non-textual; consult the page image and OCR witnesses.]"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def translation_out_dir(work_id: str, out_backend: str = OUT_BACKEND) -> Path:
    return CORPUS / work_id / "translations" / out_backend / "full"


def pages_in(text: str) -> list[int]:
    return [int(m.group(1)) for m in PAGE_RE.finditer(text)]


def page_map(full_text: str) -> dict[int, str]:
    matches = list(PAGE_RE.finditer(full_text))
    out: dict[int, str] = {}
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        out[int(match.group(1))] = full_text[start:end].strip()
    return out


def collect_pages(mapping: dict[int, str], pages: list[int]) -> str:
    parts = []
    for page in pages:
        if page in mapping:
            parts.append(f"--- Page {page:03d} ---\n{mapping[page]}")
    return "\n\n".join(parts).strip()


def replace_warned_pages(text: str, warnings_by_page: dict[int, list[str]]) -> tuple[str, list[int]]:
    matches = list(PAGE_RE.finditer(text))
    if not matches:
        return text, []

    parts: list[str] = []
    replaced: list[int] = []
    for i, match in enumerate(matches):
        page = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        if page in warnings_by_page:
            warning = "; ".join(warnings_by_page[page])
            body = (
                "[Primary Qwen3-VL OCR flagged for this page: "
                f"{warning}. Use the secondary OCR witness for translation.]"
            )
            replaced.append(page)
        else:
            body = text[start:end].strip()
        parts.append(f"--- Page {page:03d} ---\n{body}")
    return "\n\n".join(parts).strip(), replaced


def prior_chunk(work_id: str, index: int) -> str:
    candidates = [
        CORPUS / work_id / "translations" / "public" / "full" / f"full_chunk_{index:04d}.md",
        CORPUS / work_id / "translations" / "gpt-v3" / "full" / f"full_chunk_{index:04d}.md",
        CORPUS / work_id / "translations" / "minimax-v2" / "full" / f"full_chunk_{index:04d}.md",
    ]
    for path in candidates:
        if path.exists():
            return read_text(path).strip()
    return "[no prior English chunk found]"


def roman_to_int(text: str) -> int | None:
    cleaned = re.sub(r"[^ivxlcdmj]", "", text.lower()).replace("j", "i")
    if not cleaned or "m" not in cleaned:
        return None
    values = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    for index, char in enumerate(cleaned):
        value = values[char]
        next_value = values[cleaned[index + 1]] if index + 1 < len(cleaned) else 0
        total += -value if value < next_value else value
    return total if 1300 <= total <= 1699 else None


def date_years(text: str) -> list[int]:
    years = {int(match.group(1)) for match in ARABIC_YEAR_RE.finditer(text)}
    for match in ROMAN_YEAR_RE.finditer(text):
        year = roman_to_int(match.group(0))
        if year is not None:
            years.add(year)
    return sorted(years)


def date_variant_candidates(primary: str, secondary: str) -> list[str]:
    primary_years = date_years(primary)
    secondary_years = date_years(secondary)
    if primary_years and secondary_years and primary_years != secondary_years:
        return [
            "primary_years="
            + ",".join(str(year) for year in primary_years)
            + "; secondary_years="
            + ",".join(str(year) for year in secondary_years)
        ]
    return []


def alpha_count(text: str) -> int:
    return len(re.findall(r"[A-Za-zÀ-ž]", text))


def mojibake_count(text: str) -> int:
    return len(MOJIBAKE_RE.findall(text))


def unclear_count(text: str) -> int:
    return text.lower().count("[unclear]")


def output_page_count(text: str) -> int:
    return len(OUTPUT_PAGE_RE.findall(text))


def strip_leading_overlap(text: str, chunk_index: int) -> str:
    if chunk_index <= 1:
        return text
    match = OUTPUT_PAGE_RE.search(text)
    if not match or match.start() == 0:
        return text
    return text[match.start() :].lstrip()


def clean_existing_chunks(work_id: str, out_backend: str = OUT_BACKEND) -> int:
    out_dir = translation_out_dir(work_id, out_backend)
    changed = 0
    for path in sorted(out_dir.glob("full_chunk_*.md")):
        try:
            index = int(path.stem.rsplit("_", 1)[-1])
        except ValueError:
            continue
        original = read_text(path)
        cleaned = strip_leading_overlap(original, index)
        if cleaned != original:
            write_text(path, cleaned.rstrip() + "\n")
            changed += 1
    return changed


def repair_mojibake(text: str) -> str:
    repaired = text
    for bad, good in COMMON_MOJIBAKE.items():
        repaired = repaired.replace(bad, good)
    if not MOJIBAKE_RE.search(repaired):
        return repaired

    pieces = []
    for piece in repaired.splitlines(keepends=True):
        if not MOJIBAKE_RE.search(piece):
            pieces.append(piece)
            continue
        try:
            candidate = piece.encode("cp1252").decode("utf-8")
        except UnicodeError:
            pieces.append(piece)
            continue
        pieces.append(candidate if mojibake_count(candidate) < mojibake_count(piece) else piece)
    candidate = "".join(pieces)
    return candidate if mojibake_count(candidate) <= mojibake_count(text) else text


def ocr_warnings(new_full: Path) -> dict[int, list[str]]:
    metrics = new_full.with_name("qwen3vl_page_metrics.jsonl")
    warnings: dict[int, list[str]] = {}
    if not metrics.exists():
        return warnings
    latest_by_page: dict[int, dict[str, Any]] = {}
    for line in metrics.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        page = row.get("page")
        if not isinstance(page, int):
            continue
        latest_by_page[page] = row

    for page, row in latest_by_page.items():
        page_warnings: list[str] = []
        if row.get("error"):
            page_warnings.append("OCR request failed")
        usage = row.get("usage") if isinstance(row.get("usage"), dict) else {}
        completion_tokens = usage.get("completion_tokens")
        max_tokens = row.get("max_tokens", 2200)
        if row.get("capped") or (
            isinstance(completion_tokens, int)
            and isinstance(max_tokens, int)
            and completion_tokens >= max_tokens
        ):
            page_warnings.append("OCR may be truncated at max_tokens")
        if page_warnings:
            warnings[page] = page_warnings
    return warnings


def duplicate_chapter_candidates(text: str) -> list[str]:
    out = []
    last: str | None = None
    for match in CHAPTER_RE.finditer(text):
        value = match.group(1).lower()
        if value == last and value not in out:
            out.append(value)
        last = value
    return out


def alpha_count(text: str) -> int:
    return sum(1 for char in text if char.isalpha())


def translate_chunk(
    *,
    primary: str,
    secondary: str,
    prior: str,
    pages: list[int],
    timeout: int,
    effort: str,
    model: str = DEFAULT_MODEL,
) -> str | None:
    if alpha_count(primary + secondary) < 40:
        return PLACEHOLDER
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(SCHEMA, handle)
        schema_path = handle.name
    prompt = PROMPT_TEMPLATE.format(
        pages=", ".join(str(p) for p in pages) if pages else "[unknown]",
        primary=primary[:14000],
        secondary=secondary[:14000],
        prior=prior[:8000],
    )
    cmd = [
        CODEX,
        "exec",
        "-m",
        model,
        "-s",
        "read-only",
        "--skip-git-repo-check",
        "--ignore-user-config",
        "--output-schema",
        schema_path,
        "-c",
        f'model_reasoning_effort="{effort}"',
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None
    for line in reversed([line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]):
        if line.startswith("{") and line.endswith("}"):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            english = obj.get("english", "").strip()
            if english:
                return repair_mojibake(english)
    return None


def build_jobs(
    work_id: str,
    *,
    new_engine: str = NEW_ENGINE,
    fallback_secondary_on_ocr_warnings: bool = False,
) -> list[dict[str, Any]]:
    new_full = CORPUS / work_id / "translations" / "_reocr" / new_engine / "full.txt"
    old_full = CORPUS / work_id / "full.txt"
    if not new_full.exists():
        raise FileNotFoundError(new_full)
    if not old_full.exists():
        raise FileNotFoundError(old_full)

    old_pages = page_map(read_text(old_full))
    warnings_by_page = ocr_warnings(new_full)
    records = records_from_file(new_full, None, CHUNK_MAX, 0, True)
    jobs = []
    for index, record in enumerate(records, 1):
        primary = record["text"].strip()
        pages = pages_in(primary)
        warnings = []
        chunk_warnings_by_page: dict[int, list[str]] = {}
        secondary_missing_pages = []
        for page in pages:
            page_warnings = warnings_by_page.get(page, [])
            if page_warnings:
                chunk_warnings_by_page[page] = page_warnings
            if page_warnings and alpha_count(old_pages.get(page, "")) < 40:
                secondary_missing_pages.append(page)
            for warning in page_warnings:
                warnings.append(f"page {page:03d}: {warning}")
        primary_for_translation = primary
        secondary_fallback_pages: list[int] = []
        if fallback_secondary_on_ocr_warnings and chunk_warnings_by_page:
            primary_for_translation, secondary_fallback_pages = replace_warned_pages(
                primary,
                chunk_warnings_by_page,
            )
        secondary = collect_pages(old_pages, pages)
        jobs.append(
            {
                "index": index,
                "pages": pages,
                "primary": primary_for_translation,
                "secondary": secondary,
                "prior": prior_chunk(work_id, index),
                "ocr_warnings": warnings,
                "blocking_ocr_warnings": warnings
                if not fallback_secondary_on_ocr_warnings or secondary_missing_pages
                else [],
                "primary_ocr_failed_pages": sorted(chunk_warnings_by_page),
                "secondary_fallback_pages": secondary_fallback_pages,
                "secondary_fallback_missing_pages": secondary_missing_pages,
                "duplicate_chapter_candidates": duplicate_chapter_candidates(primary),
                "date_variant_candidates": date_variant_candidates(primary, secondary),
            }
        )
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_id")
    parser.add_argument("--new-engine", default=NEW_ENGINE)
    parser.add_argument("--out-backend", default=None,
                        help="Translation output backend dir name. Defaults to a name "
                             "derived from --model (e.g. qwen3vl-dual-gpt56-sol).")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help="Codex model to translate with (e.g. gpt-5.5, gpt-5.6-sol).")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--effort", default="high", choices=["low", "medium", "high"])
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--allow-ocr-warnings",
        action="store_true",
        help="Translate even when source OCR metrics report failed or capped pages.",
    )
    parser.add_argument(
        "--fallback-secondary-on-ocr-warnings",
        action="store_true",
        help="Replace failed/capped primary OCR pages with an instruction to use the secondary OCR witness.",
    )
    parser.add_argument(
        "--clean-existing",
        action="store_true",
        help="Strip leading overlap before the first page marker in existing translated chunks.",
    )
    parser.add_argument(
        "--strict-output-guards",
        action="store_true",
        help="Refuse to cache chunks with marker drift/drop, preambles, loops, or enabled anchor failures.",
    )
    parser.add_argument(
        "--require-source-anchor",
        action="store_true",
        help="Require at least one source proper-name/numeric anchor to survive in each translated chunk.",
    )
    args = parser.parse_args()

    # Derive a backend name from the model when none is given, so each model's
    # output lands in its own directory (e.g. gpt-5.6-sol -> qwen3vl-dual-gpt56-sol)
    # and never overwrites a prior lane.
    if not args.out_backend:
        model_slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower()).strip("-")
        model_slug = model_slug.replace("gpt-", "gpt").replace("5-6", "56").replace("5-5", "55")
        args.out_backend = f"qwen3vl-dual-{model_slug}"

    if args.clean_existing:
        changed = clean_existing_chunks(args.work_id, args.out_backend)
        print(f"{args.work_id}: cleaned {changed} existing chunk(s)")
        return 0

    jobs = build_jobs(
        args.work_id,
        new_engine=args.new_engine,
        fallback_secondary_on_ocr_warnings=args.fallback_secondary_on_ocr_warnings,
    )
    blocked = [job for job in jobs if job["blocking_ocr_warnings"]]
    if blocked and not args.allow_ocr_warnings:
        print("Refusing to translate chunks with OCR warnings:", file=sys.stderr)
        for job in blocked:
            print(
                f"  chunk {job['index']:04d}: {', '.join(job['blocking_ocr_warnings'])}",
                file=sys.stderr,
            )
        print(
            "Re-run/fix those OCR pages, pass --allow-ocr-warnings, or use "
            "--fallback-secondary-on-ocr-warnings when secondary OCR is available.",
            file=sys.stderr,
        )
        return 2

    out_dir = translation_out_dir(args.work_id, args.out_backend)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "runs.jsonl"
    todo = [
        job
        for job in jobs
        if args.force or not (out_dir / f"full_chunk_{job['index']:04d}.md").exists()
    ]
    print(f"{args.work_id}: {len(jobs)} chunks, {len(todo)} to translate -> {out_dir}", flush=True)

    def run(job: dict[str, Any]) -> tuple[int, bool, dict[str, Any]]:
        index = job["index"]
        english = translate_chunk(
            primary=job["primary"],
            secondary=job["secondary"],
            prior=job["prior"],
            pages=job["pages"],
            timeout=args.timeout,
            effort=args.effort,
            model=args.model,
        )
        ok = bool(english)
        guard = validate_translation_output(
            output_text=english or "",
            expected_pages=job["pages"],
            source_text=job["primary"],
            require_source_anchor=args.require_source_anchor,
        )
        if english:
            english = strip_leading_overlap(english, index)
            guard = validate_translation_output(
                output_text=english,
                expected_pages=job["pages"],
                source_text=job["primary"],
                require_source_anchor=args.require_source_anchor,
            )
            if args.strict_output_guards and guard["blocking_issues"]:
                ok = False
            else:
                write_text(out_dir / f"full_chunk_{index:04d}.md", english.rstrip() + "\n")
        return index, ok, {
            "chunk": index,
            "model": args.model,
            "effort": args.effort,
            "pages": job["pages"],
            "primary_chars": len(job["primary"]),
            "secondary_chars": len(job["secondary"]),
            "prior_chars": len(job["prior"]),
            "ocr_warnings": job["ocr_warnings"],
            "blocking_ocr_warnings": job["blocking_ocr_warnings"],
            "primary_ocr_failed_pages": job["primary_ocr_failed_pages"],
            "secondary_fallback_pages": job["secondary_fallback_pages"],
            "secondary_fallback_missing_pages": job["secondary_fallback_missing_pages"],
            "duplicate_chapter_candidates": job["duplicate_chapter_candidates"],
            "date_variant_candidates": job["date_variant_candidates"],
            "unclear_count": unclear_count(english or ""),
            "mojibake_markers": mojibake_count(english or ""),
            "output_page_markers": output_page_count(english or ""),
            "output_guard": guard,
            "ok": ok,
        }

    failures = []
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run, job): job for job in todo}
        for future in as_completed(futures):
            index, ok, record = future.result()
            done += 1
            if not ok:
                failures.append(index)
            with manifest.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"  [{done:3}/{len(todo)}] chunk {index:04d} {'ok' if ok else 'FAIL'}", flush=True)

    print(f"DONE {args.work_id}: translated={done - len(failures)} failed={len(failures)} {failures[:20]}", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
