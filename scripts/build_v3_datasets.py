"""Build V3 Trithemius-first OCR and Latin translation datasets.

V3 emits three versioned interfaces under data/v3/:

* v3_ocr_pages.jsonl
* v3_translation_pairs.jsonl
* v3_eval_cases.jsonl

The builder is deliberately conservative. It admits OCR pages only from
teacher-like local rows or strong witness agreement, disables the corrupted
Vulgate/DRB V2 source, filters external parallel rows, and moves second-pass
failures into eval rather than positive training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"

V3_TARGETS = {
    "ocr": {"train": 4800, "validation": 600, "test": 600},
}

HOLDOUT_WORKS = {
    "prdl-24376_ecloga-de-laude-calvorum-ad-carolum",
    "prdl-24364_de-laudibus-sanctissimae-matris-annae",
    "prdl-24362_de-laude-scriptorum-manualium",
    "prdl-70291_dilibri_veterum-sophorum-sigilla-et-imagines-magicae",
}

PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’-]{1,}")
GREEK_HEBREW_RE = re.compile(r"[\u0370-\u03ff\u0590-\u05ff]")

LATIN_HINTS = {
    "et",
    "in",
    "non",
    "qui",
    "quae",
    "quod",
    "cum",
    "est",
    "sunt",
    "esse",
    "ad",
    "per",
    "de",
    "ut",
    "autem",
    "enim",
    "hoc",
    "illa",
    "ipse",
    "dominus",
}

ENGLISH_HINTS = {
    "a",
    "an",
    "are",
    "as",
    "be",
    "but",
    "by",
    "even",
    "had",
    "has",
    "have",
    "he",
    "i",
    "into",
    "is",
    "it",
    "my",
    "of",
    "or",
    "so",
    "than",
    "the",
    "and",
    "that",
    "to",
    "with",
    "shall",
    "which",
    "for",
    "not",
    "this",
    "from",
    "his",
    "her",
    "their",
    "you",
    "was",
    "were",
}

NON_LATIN_HINTS = {
    "und",
    "der",
    "die",
    "das",
    "nicht",
    "ein",
    "eine",
    "avec",
    "pour",
    "que",
    "les",
    "des",
    "vous",
    "nous",
    "par",
    "qui",
}

BOOTSTRAP_CONFUSION_MATRIX = {
    "version": "bootstrap_confusion_v1",
    "notes": "Seeded from common early-print OCR confusions; replace with measured V3 OCR/reference alignments when available.",
    "substitutions": [
        {"from": "s", "to": "f", "weight": 0.18},
        {"from": "f", "to": "s", "weight": 0.06},
        {"from": "u", "to": "v", "weight": 0.12},
        {"from": "v", "to": "u", "weight": 0.10},
        {"from": "i", "to": "j", "weight": 0.08},
        {"from": "j", "to": "i", "weight": 0.08},
        {"from": "ae", "to": "e", "weight": 0.05},
        {"from": "oe", "to": "e", "weight": 0.04},
        {"from": "rn", "to": "m", "weight": 0.04},
        {"from": "m", "to": "rn", "weight": 0.02},
        {"from": "ct", "to": "cl", "weight": 0.03},
    ],
    "profiles": {
        "light_bootstrap_confusion_v1": {"rate": 0.010},
        "medium_bootstrap_confusion_v1": {"rate": 0.025},
    },
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def stable_hash(*parts: object, length: int = 16) -> str:
    payload = "::".join(str(part) for part in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: object) -> str:
    return f"{prefix}-{stable_hash(*parts)}"


def split_for_family(family: str, forced_test: bool = False) -> str:
    if forced_test or family in HOLDOUT_WORKS:
        return "test"
    value = int(hashlib.sha1(family.encode("utf-8")).hexdigest()[:8], 16) % 100
    if value < 10:
        return "validation"
    if value < 20:
        return "test"
    return "train"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compact_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def alpha_count(text: str) -> int:
    return sum(1 for char in (text or "") if char.isalpha())


def words(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text or "")]


def looks_latin(text: str) -> bool:
    toks = words(text)
    if len(toks) < 4:
        return False
    latin_hits = sum(1 for token in toks[:250] if token in LATIN_HINTS or token.endswith(("um", "us", "ae", "is", "ibus")))
    english_hits = sum(1 for token in toks[:250] if token in ENGLISH_HINTS)
    return latin_hits >= max(2, english_hits)


def looks_english(text: str) -> bool:
    toks = words(text)
    if len(toks) < 4:
        return False
    hits = sum(1 for token in toks[:250] if token in ENGLISH_HINTS)
    return hits >= 1 if len(toks) < 12 else hits >= 2


def mixed_language_flags(text: str) -> list[str]:
    flags: list[str] = []
    if GREEK_HEBREW_RE.search(text or ""):
        flags.append("greek_or_hebrew_quarantine")
    toks = words(text)
    if toks:
        nonlatin_hits = sum(1 for token in toks[:250] if token in NON_LATIN_HINTS)
        latin_hits = sum(1 for token in toks[:250] if token in LATIN_HINTS)
        if nonlatin_hits >= 8 and nonlatin_hits > latin_hits:
            flags.append("german_french_heavy_quarantine")
    return flags


def page_map(text: str) -> dict[int, str]:
    pages: dict[int, list[str]] = {}
    current: int | None = None
    buffer: list[str] = []
    for line in (text or "").splitlines():
        match = PAGE_RE.match(line.strip())
        if match:
            if current is not None:
                pages[current] = buffer
            current = int(match.group(1))
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        pages[current] = buffer
    return {page: "\n".join(lines).strip() for page, lines in pages.items()}


def pages_in(text: str) -> list[int]:
    return [int(match.group(1)) for match in PAGE_RE.finditer(text or "")]


def collect_pages(pages: dict[int, str], wanted: list[int]) -> str:
    parts = []
    for page in wanted:
        body = pages.get(page, "").strip()
        if body:
            parts.append(f"--- Page {page:03d} ---\n{body}")
    return "\n\n".join(parts).strip()


def normalized_for_agreement(text: str) -> str:
    text = compact_space(text).lower()
    text = text.replace("ſ", "s")
    return re.sub(r"[^a-z0-9]+", "", text)


def similarity(left: str, right: str) -> float:
    a = normalized_for_agreement(left)
    b = normalized_for_agreement(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if max(len(a), len(b)) / max(1, min(len(a), len(b))) > 2.25:
        return 0.0
    a = a[:5000]
    b = b[:5000]
    width = 5
    a_grams = {a[i : i + width] for i in range(0, max(0, len(a) - width + 1), 2)}
    b_grams = {b[i : i + width] for i in range(0, max(0, len(b) - width + 1), 2)}
    if not a_grams or not b_grams:
        return 0.0
    return (2.0 * len(a_grams & b_grams)) / (len(a_grams) + len(b_grams))


def is_blank_label(text: str, min_alpha: int) -> bool:
    lowered = compact_space(text).lower()
    return lowered in {"", "[blank page]", "blank page"} or alpha_count(text) < min_alpha


def witness_flags(text: str, min_alpha: int) -> list[str]:
    flags = []
    if is_blank_label(text, min_alpha):
        flags.append("blank_or_tiny")
    if text.count("[unclear]") >= 5:
        flags.append("many_unclear_spans")
    if "\ufffd" in text:
        flags.append("replacement_char")
    flags.extend(mixed_language_flags(text))
    return flags


def choose_ocr_label(
    witnesses: list[dict[str, Any]],
    *,
    min_alpha: int,
    agreement_threshold: float,
) -> tuple[str | None, str | None, float, list[str]]:
    usable = [w for w in witnesses if w.get("text")]
    if not usable:
        return None, None, 0.0, ["no_witness_text"]

    blanks = [w for w in usable if is_blank_label(str(w["text"]), min_alpha)]
    nonblanks = [w for w in usable if not is_blank_label(str(w["text"]), min_alpha)]
    if len(blanks) >= 2 and not nonblanks:
        return "[blank page]", "blank_witness_agreement", 0.98, ["blank_page"]
    if blanks and nonblanks:
        return None, None, 0.0, ["blank_disagreement"]

    best: tuple[float, dict[str, Any], dict[str, Any]] | None = None
    for i, left in enumerate(nonblanks):
        for right in nonblanks[i + 1 :]:
            score = similarity(str(left["text"]), str(right["text"]))
            if best is None or score > best[0]:
                best = (score, left, right)
    if best is None or best[0] < agreement_threshold:
        return None, None, 0.0, ["no_strong_witness_agreement"]

    _, left, right = best
    chosen = left if len(str(left["text"])) >= len(str(right["text"])) else right
    text = str(chosen["text"]).strip()
    flags = sorted(set(witness_flags(text, min_alpha)))
    quarantine = [flag for flag in flags if flag.endswith("_quarantine")]
    if quarantine:
        return None, None, 0.0, quarantine
    confidence = min(0.99, 0.70 + best[0] * 0.25)
    method = f"strong_witness_agreement:{left['name']}+{right['name']}"
    return text, method, round(confidence, 3), flags


def page_type(label_text: str) -> str:
    text = label_text or ""
    lower = text.lower()
    if is_blank_label(text, 20):
        return "blank"
    if any(term in lower for term in ("tabula", "table", "|", "folio and line")):
        return "table_or_layout"
    if any(term in lower for term in ("cipher", "alphabet", "clavis", "steganograph")):
        return "cipher_or_alphabet"
    if text.count("[unclear]") >= 3 or "\ufffd" in text:
        return "damaged_or_unclear"
    if alpha_count(text) < 900 and any(term in lower[:900] for term in ("title", "privileg", "lector", "dedicat")):
        return "title_or_prefatory"
    return "body_text_latin"


def source_url_for_work(work_id: str) -> str:
    return f"local://{(CORPUS / work_id).as_posix()}"


def license_for_local_work() -> str:
    return "project-internal-public-domain-derived; see local corpus provenance"


def qwen_page_maps(work_dir: Path) -> tuple[str | None, dict[int, str]]:
    candidates = [
        work_dir / "translations" / "_reocr" / "qwen3vl-4b-trithemius-q6" / "full.txt",
        work_dir / "translations" / "_reocr" / "qwen3vl-4b-instruct-q6" / "full.txt",
        work_dir / "translations" / "_reocr" / "qwen25vl-7b-q6k" / "full.txt",
    ]
    for path in candidates:
        if path.exists():
            return path.parent.name, page_map(read_text(path))
    return None, {}


def build_ocr_pages(args: argparse.Namespace) -> tuple[list[dict[str, Any]], Counter]:
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    if not CORPUS.exists():
        rejected["missing_corpus_root"] += 1
        return rows, rejected

    work_dirs = sorted(path for path in CORPUS.iterdir() if path.is_dir() and (path / "pages").is_dir())
    for work_dir in work_dirs:
        work_id = work_dir.name
        qwen_name, qwen_pages = qwen_page_maps(work_dir)
        existing_pages = page_map(read_text(work_dir / "full.txt")) if (work_dir / "full.txt").exists() else {}
        churro_pages = page_map(read_text(work_dir / "churro_full.txt")) if (work_dir / "churro_full.txt").exists() else {}
        images = sorted((work_dir / "pages").glob("page_*.png")) + sorted((work_dir / "pages").glob("page_*.jpg"))
        for image in images:
            match = re.search(r"page_0*(\d+)", image.stem)
            if not match:
                rejected["image_name_without_page"] += 1
                continue
            page = int(match.group(1))
            witnesses = [
                {"name": qwen_name or "qwen_missing", "text": qwen_pages.get(page, "")},
                {"name": "existing_corpus", "text": existing_pages.get(page, "")},
                {"name": "churro", "text": churro_pages.get(page, "")},
            ]
            label, method, confidence, flags = choose_ocr_label(
                witnesses,
                min_alpha=args.min_ocr_alpha,
                agreement_threshold=args.ocr_agreement_threshold,
            )
            if label is None or method is None:
                for flag in flags:
                    rejected[flag] += 1
                continue
            split = split_for_family(f"ocr:{work_id}", forced_test=work_id in HOLDOUT_WORKS)
            row = {
                "id": f"v3ocr-{stable_hash(work_id, page)}",
                "split": split,
                "work_id": work_id,
                "page_id": f"page_{page:04d}",
                "page_type": page_type(label),
                "image_path": image.as_posix(),
                "image_sha256": sha256_file(image),
                "source_url": source_url_for_work(work_id),
                "license": license_for_local_work(),
                "witnesses": [
                    {
                        "name": witness["name"],
                        "text_sha1": stable_hash(witness.get("text", ""), length=40) if witness.get("text") else None,
                        "chars": len(witness.get("text", "")),
                        "flags": witness_flags(str(witness.get("text", "")), args.min_ocr_alpha),
                    }
                    for witness in witnesses
                ],
                "label_text": label,
                "label_method": method,
                "label_confidence": confidence,
                "reject_flags": flags,
            }
            rows.append(row)
            if args.max_ocr_pages and len(rows) >= args.max_ocr_pages:
                return rows, rejected
    return rows, rejected


def _pick_whole_work_bucket(
    candidates: dict[str, int],
    target: int,
    *,
    salt: str,
) -> set[str]:
    selected: set[str] = set()
    total = 0
    remaining = set(candidates)
    while remaining and total < target:
        best = min(
            remaining,
            key=lambda work_id: (
                abs(target - (total + candidates[work_id])),
                int(hashlib.sha1(f"{salt}:{work_id}".encode("utf-8")).hexdigest()[:8], 16),
            ),
        )
        selected.add(best)
        total += candidates[best]
        remaining.remove(best)
    return selected


def rebalance_ocr_splits(rows: list[dict[str, Any]]) -> None:
    """Assign OCR splits by whole works while keeping holdout buckets useful."""

    counts = Counter(str(row["work_id"]) for row in rows)
    fixed_test = {work_id for work_id in counts if work_id in HOLDOUT_WORKS}
    fixed_test_count = sum(counts[work_id] for work_id in fixed_test)
    candidates = {work_id: count for work_id, count in counts.items() if work_id not in fixed_test}

    validation = _pick_whole_work_bucket(
        candidates,
        V3_TARGETS["ocr"]["validation"],
        salt="v3-validation",
    )
    remaining = {work_id: count for work_id, count in candidates.items() if work_id not in validation}
    test_extra = _pick_whole_work_bucket(
        remaining,
        max(0, V3_TARGETS["ocr"]["test"] - fixed_test_count),
        salt="v3-test",
    )
    test = fixed_test | test_extra

    for row in rows:
        work_id = str(row["work_id"])
        if work_id in validation:
            row["split"] = "validation"
        elif work_id in test:
            row["split"] = "test"
        else:
            row["split"] = "train"


def length_ratio_ok(latin: str, english: str, low: float = 0.30, high: float = 3.50) -> bool:
    if alpha_count(latin) < 20 or alpha_count(english) < 20:
        return False
    ratio = len(english) / max(1, len(latin))
    return low <= ratio <= high


def translation_row(
    *,
    source_key: str,
    split_family: str,
    work_id: str,
    chunk_id: str,
    input_latin: str,
    input_kind: str,
    output_english: str,
    label_method: str,
    grade_provenance: dict[str, Any],
    source_weight: float,
    tags: list[str],
    noise_profile: str = "clean",
) -> dict[str, Any]:
    return {
        "id": f"v3tr-{stable_hash(source_key, work_id, chunk_id, noise_profile, input_latin[:80])}",
        "split": split_for_family(split_family),
        "work_id": work_id,
        "chunk_id": chunk_id,
        "input_latin": input_latin.strip(),
        "input_kind": input_kind,
        "noise_profile": noise_profile,
        "output_english": output_english.strip(),
        "label_method": label_method,
        "grade_provenance": grade_provenance,
        "source_weight": source_weight,
        "tags": tags,
    }


def build_public_translation_pairs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], Counter]:
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    ledger = ROOT / "data" / "_quality" / "public_release_chunks.jsonl"
    for item in read_jsonl(ledger):
        if item.get("translation_backend") != "public":
            rejected["non_public_backend"] += 1
            continue
        if item.get("hallucinated") or item.get("preamble") or item.get("refusal"):
            rejected["release_quality_flag"] += 1
            continue
        faith = float(item.get("adj_faith") or 0)
        if faith < args.min_release_faith:
            rejected["release_faith_below_threshold"] += 1
            continue
        work_id = str(item.get("work_id") or "")
        record = str(item.get("record") or "")
        if not work_id or not record:
            rejected["release_missing_work_or_record"] += 1
            continue
        work_dir = CORPUS / work_id
        english_path = work_dir / "translations" / "public" / "full" / f"{record}.md"
        if not english_path.exists():
            rejected["release_translation_missing"] += 1
            continue
        english = read_text(english_path).strip()
        pages = pages_in(english)
        if not pages:
            rejected["release_marker_missing"] += 1
            continue
        _, ocr_pages = qwen_page_maps(work_dir)
        if not ocr_pages and (work_dir / "full.txt").exists():
            ocr_pages = page_map(read_text(work_dir / "full.txt"))
        latin = collect_pages(ocr_pages, pages)
        if not length_ratio_ok(latin, english, 0.25, 3.75):
            rejected["release_length_ratio_outlier"] += 1
            continue
        rows.append(
            translation_row(
                source_key="public_release",
                split_family=f"trithemius:{work_id}",
                work_id=work_id,
                chunk_id=record,
                input_latin=latin,
                input_kind="corrected_ocr_chunk",
                output_english=english,
                label_method="release_certified_translation",
                grade_provenance={
                    "source_file": ledger.as_posix(),
                    "evidence_source": item.get("evidence_source"),
                    "adj_faith": item.get("adj_faith"),
                    "adj_fluent": item.get("adj_fluent"),
                    "hallucinated": item.get("hallucinated"),
                    "translation_path": english_path.as_posix(),
                },
                source_weight=1.0,
                tags=["trithemius", "release_certified", "target_register"],
            )
        )
    return rows, rejected


def build_unified_clean_pairs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], Counter]:
    path = ROOT / "training_unified_clean.jsonl"
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    rejected: Counter[str] = Counter()
    for item in read_jsonl(path):
        source = str(item.get("source") or "unified")
        work_id = str(item.get("work_id") or "")
        chunk = str(item.get("chunk") or "0")
        output = str(item.get("output") or "")
        if not work_id or not output:
            rejected["unified_missing_work_or_output"] += 1
            continue
        groups[(source, work_id, chunk)].append(item)

    rows: list[dict[str, Any]] = []
    for (source, work_id, chunk), items in groups.items():
        output = str(items[0].get("output") or "").strip()
        pages = []
        pieces = []
        for item in sorted(items, key=lambda row: int(row.get("page") or 0)):
            page = int(item.get("page") or 0)
            latin = str((item.get("input") or {}).get("latin_ocr") or "").strip()
            if page and latin:
                pages.append(page)
                pieces.append(f"--- Page {page:04d} ---\n{latin}")
        out_pages = pages_in(output)
        if out_pages and sorted(set(out_pages)) != sorted(set(pages)):
            rejected["unified_marker_page_mismatch"] += 1
            continue
        input_latin = "\n\n".join(pieces).strip()
        if not length_ratio_ok(input_latin, output, 0.25, 3.75):
            rejected["unified_length_ratio_outlier"] += 1
            continue
        if not looks_english(output):
            rejected["unified_output_language_fail"] += 1
            continue
        row0 = items[0]
        tier = str(row0.get("tier") or "clean")
        rows.append(
            translation_row(
                source_key=f"unified:{source}",
                split_family=f"unified:{source}:{work_id}",
                work_id=work_id,
                chunk_id=f"chunk_{chunk}",
                input_latin=input_latin,
                input_kind="curated_ocr_chunk",
                output_english=output,
                label_method="curated_clean_pair_with_marker_check",
                grade_provenance={
                    "source_file": path.as_posix(),
                    "tier": tier,
                    "grade_faith": row0.get("grade_faith"),
                    "grade_fluent": row0.get("grade_fluent"),
                },
                source_weight=0.95 if tier == "gold" else 0.85,
                tags=[source, "target_register", tier],
            )
        )
    return rows, rejected


def split_long_pair(latin: str, english: str, max_chars: int) -> list[tuple[str, str]]:
    if len(latin) <= max_chars and len(english) <= max_chars * 2:
        return [(latin, english)]
    latin_parts = [part.strip() for part in re.split(r"\n\s*\n", latin) if part.strip()]
    english_parts = [part.strip() for part in re.split(r"\n\s*\n", english) if part.strip()]
    if len(latin_parts) == len(english_parts) and len(latin_parts) > 1:
        return list(zip(latin_parts, english_parts))
    latin_sents = [part.strip() for part in re.split(r"(?<=[.;:?!])\s+", latin) if part.strip()]
    english_sents = [part.strip() for part in re.split(r"(?<=[.;:?!])\s+", english) if part.strip()]
    if len(latin_sents) == len(english_sents) and len(latin_sents) > 1:
        return list(zip(latin_sents, english_sents))
    return []


def build_v2_external_pairs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], Counter]:
    path = ROOT / "training_v2.jsonl"
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    classical_seen = 0
    for line_no, item in enumerate(read_jsonl(path), 1):
        source_id = str(item.get("source_id") or "")
        latin = compact_space(str(item.get("latin_ocr") or ""))
        english = compact_space(str(item.get("english_translation") or ""))
        source_file = str(item.get("source_file") or source_id)
        if source_id == "vulgate-drb":
            rejected["vulgate_drb_disabled_pending_reference_alignment"] += 1
            continue
        if source_id == "grosenthal-classical":
            if classical_seen >= args.max_external_classical:
                rejected["grosenthal_cap"] += 1
                continue
            if not length_ratio_ok(latin, english, 0.30, 3.00):
                rejected["grosenthal_length_ratio_outlier"] += 1
                continue
            if not looks_latin(latin) or not looks_english(english):
                rejected["grosenthal_language_check_fail"] += 1
                continue
            classical_seen += 1
            rows.append(
                translation_row(
                    source_key="grosenthal_filtered",
                    split_family=f"grosenthal:{source_file}",
                    work_id=f"grosenthal-{source_file}",
                    chunk_id=f"line_{line_no}",
                    input_latin=latin,
                    input_kind="external_clean_latin",
                    output_english=english,
                    label_method="external_parallel_filtered",
                    grade_provenance={
                        "source_file": path.as_posix(),
                        "external_source": "grosenthal/latin_english_parallel",
                        "line_no": line_no,
                        "adj_faith": item.get("adj_faith"),
                        "adj_fluent": item.get("adj_fluent"),
                    },
                    source_weight=0.55,
                    tags=["external", "classical_latin", "filtered_alignment"],
                )
            )
            continue
        if source_id.startswith("benedict-"):
            chunks = split_long_pair(latin, english, args.max_pair_chars)
            if not chunks:
                rejected["benedict_long_pair_unsplittable"] += 1
                continue
            for idx, (la, en) in enumerate(chunks, 1):
                if not length_ratio_ok(la, en, 0.30, 3.25):
                    rejected["benedict_length_ratio_outlier"] += 1
                    continue
                if not looks_latin(la) or not looks_english(en):
                    rejected["benedict_language_check_fail"] += 1
                    continue
                rows.append(
                    translation_row(
                        source_key="benedict_filtered",
                        split_family=f"benedict:{source_id}",
                        work_id=f"benedict-{source_id}",
                        chunk_id=f"{source_id}_{idx:03d}",
                        input_latin=la,
                        input_kind="external_clean_latin",
                        output_english=en,
                        label_method="external_public_domain_split_checked",
                        grade_provenance={
                            "source_file": path.as_posix(),
                            "line_no": line_no,
                            "split_method": "paragraph_or_sentence_equal_count",
                        },
                        source_weight=0.70,
                        tags=["external", "benedictine", "public_domain"],
                    )
                )
            continue
        rejected["unknown_v2_source"] += 1
    return rows, rejected


def build_anchor_pairs() -> tuple[list[dict[str, Any]], Counter]:
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    for path in sorted((ROOT / "data" / "anchors").glob("*.jsonl")):
        for item in read_jsonl(path):
            latin = compact_space(str(item.get("latin") or ""))
            english = compact_space(str(item.get("english") or ""))
            if not length_ratio_ok(latin, english, 0.20, 4.00):
                rejected["anchor_length_ratio_outlier"] += 1
                continue
            if not looks_latin(latin) or not looks_english(english):
                rejected["anchor_language_check_fail"] += 1
                continue
            latin_source = item.get("latin_source") if isinstance(item.get("latin_source"), dict) else {}
            english_source = item.get("english_source") if isinstance(item.get("english_source"), dict) else {}
            rows.append(
                translation_row(
                    source_key="anchor",
                    split_family=f"anchor:{path.stem}",
                    work_id=f"anchor-{path.stem}",
                    chunk_id=str(item.get("id") or stable_hash(latin, english)),
                    input_latin=latin,
                    input_kind="reference_anchor_latin",
                    output_english=english,
                    label_method="public_domain_reference_anchor",
                    grade_provenance={
                        "source_file": path.as_posix(),
                        "latin_source_url": latin_source.get("url"),
                        "english_source_url": english_source.get("url"),
                        "public_domain": bool(latin_source.get("public_domain")) and bool(english_source.get("public_domain")),
                    },
                    source_weight=0.80,
                    tags=["anchor", path.stem],
                )
            )
    return rows, rejected


def noise_should_change(text: str, pos: int, profile_rate: float, seed: str) -> bool:
    value = int(hashlib.sha1(f"{seed}:{pos}".encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    return value < profile_rate


def apply_noise(text: str, profile: str, seed: str) -> str:
    profile_cfg = BOOTSTRAP_CONFUSION_MATRIX["profiles"][profile]
    rate = float(profile_cfg["rate"])
    substitutions = BOOTSTRAP_CONFUSION_MATRIX["substitutions"]
    lines = []
    cursor = 0
    for line in (text or "").splitlines():
        if PAGE_RE.match(line.strip()):
            lines.append(line)
            cursor += len(line) + 1
            continue
        out = line
        for sub_idx, sub in enumerate(substitutions):
            src = str(sub["from"])
            dst = str(sub["to"])
            pieces = []
            i = 0
            while i < len(out):
                if out.startswith(src, i) and noise_should_change(text, cursor + i + sub_idx * 17, rate * float(sub["weight"]) * 6, seed):
                    pieces.append(dst)
                    i += len(src)
                else:
                    pieces.append(out[i])
                    i += 1
            out = "".join(pieces)
        lines.append(out)
        cursor += len(line) + 1
    return "\n".join(lines)


def add_noise_variants(rows: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    candidates = [
        row
        for row in rows
        if row["split"] == "train"
        and row["noise_profile"] == "clean"
        and any(tag in row["tags"] for tag in ("target_register", "trithemius", "anchor"))
    ]
    for row in candidates[: args.noise_source_limit]:
        for profile in ("light_bootstrap_confusion_v1", "medium_bootstrap_confusion_v1"):
            noisy = apply_noise(row["input_latin"], profile, row["id"])
            if noisy == row["input_latin"]:
                continue
            new_row = dict(row)
            new_row["id"] = f"v3tr-{stable_hash(row['id'], profile)}"
            new_row["input_latin"] = noisy
            new_row["input_kind"] = "synthetic_ocr_confusion_variant"
            new_row["noise_profile"] = profile
            new_row["source_weight"] = round(float(row["source_weight"]) * 0.85, 3)
            new_row["tags"] = sorted(set(row["tags"] + ["synthetic_ocr_noise", "bootstrap_confusion_matrix"]))
            variants.append(new_row)
    return rows + variants


def second_pass_roots() -> list[Path]:
    return [
        ROOT / "trithemius_corpus_grading_package_2026-07-05_SECOND_PASS" / "trithemius_corpus_grading_package_2026-07-05" / "02_first_pass_grades",
        Path(r"C:\Users\Ian\Downloads\trithemius_2ndpass_RESULTS\trithemius_2ndpass\02_first_pass_grades"),
    ]


def build_eval_cases(ocr_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter]:
    rows: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    for row in ocr_rows:
        if row["split"] not in {"validation", "test"}:
            continue
        rows.append(
            {
                "id": f"v3eval-{stable_hash('ocr', row['id'])}",
                "task": "ocr",
                "split": row["split"],
                "work_id": row["work_id"],
                "failure_modes": [row["page_type"]] + list(row.get("reject_flags") or []),
                "input_refs": {"image_path": row["image_path"], "image_sha256": row["image_sha256"], "page_id": row["page_id"]},
                "expected_output": row["label_text"],
                "gate_group": "ocr_holdout",
            }
        )

    grade_root = next((root for root in second_pass_roots() if root.exists()), None)
    if not grade_root:
        rejected["second_pass_root_missing"] += 1
        return rows, rejected
    for path in sorted(grade_root.glob("*/second_pass_grades.jsonl")):
        for item in read_jsonl(path):
            issues = list(item.get("issues") or [])
            faithful = int(item.get("faithful") or 0)
            hallucinated = bool(item.get("hallucinated"))
            hard = hallucinated or faithful <= 3 or any(
                issue in issues
                for issue in (
                    "page_drift",
                    "marker_drop",
                    "factual_hallucination",
                    "repetition_loop",
                    "faithful_omission",
                    "structural_break",
                )
            )
            if not hard:
                continue
            work_id = str(item.get("work") or path.parent.name)
            chunk = item.get("chunk")
            rows.append(
                {
                    "id": f"v3eval-{stable_hash('second_pass', work_id, chunk, json.dumps(issues, sort_keys=True))}",
                    "task": "translation",
                    "split": "test",
                    "work_id": work_id,
                    "failure_modes": sorted(set(issues + (["hallucination"] if hallucinated else []))),
                    "input_refs": {
                        "grade_path": path.as_posix(),
                        "chunk": chunk,
                        "pages": item.get("pages") or [],
                    },
                    "expected_output": {
                        "minimum_faithful": 4,
                        "must_preserve_page_markers": True,
                        "must_not_hallucinate": True,
                        "grader_reason": item.get("reason"),
                    },
                    "gate_group": "second_pass_hard_cases",
                }
            )
    return rows, rejected


def summarize(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key)) for row in rows).items()))


def build(args: argparse.Namespace) -> dict[str, Any]:
    args.out.mkdir(parents=True, exist_ok=True)
    rejects: dict[str, dict[str, int]] = {}

    ocr_rows, ocr_rejects = build_ocr_pages(args)
    rebalance_ocr_splits(ocr_rows)
    rejects["ocr"] = dict(sorted(ocr_rejects.items()))

    translation_rows: list[dict[str, Any]] = []
    for name, builder in (
        ("public_release", lambda: build_public_translation_pairs(args)),
        ("unified_clean", lambda: build_unified_clean_pairs(args)),
        ("v2_external", lambda: build_v2_external_pairs(args)),
        ("anchors", build_anchor_pairs),
    ):
        rows, row_rejects = builder()
        translation_rows.extend(rows)
        rejects[name] = dict(sorted(row_rejects.items()))

    before_noise = len(translation_rows)
    translation_rows = add_noise_variants(translation_rows, args)
    noise_added = len(translation_rows) - before_noise

    eval_rows, eval_rejects = build_eval_cases(ocr_rows)
    rejects["eval"] = dict(sorted(eval_rejects.items()))

    write_jsonl(args.out / "v3_ocr_pages.jsonl", ocr_rows)
    write_jsonl(args.out / "v3_translation_pairs.jsonl", translation_rows)
    write_jsonl(args.out / "v3_eval_cases.jsonl", eval_rows)
    write_json(args.out / "latin_ocr_confusion_matrix.json", BOOTSTRAP_CONFUSION_MATRIX)

    manifest = {
        "version": "v3",
        "created_by": "scripts/build_v3_datasets.py",
        "paths": {
            "ocr_pages": (args.out / "v3_ocr_pages.jsonl").as_posix(),
            "translation_pairs": (args.out / "v3_translation_pairs.jsonl").as_posix(),
            "eval_cases": (args.out / "v3_eval_cases.jsonl").as_posix(),
            "confusion_matrix": (args.out / "latin_ocr_confusion_matrix.json").as_posix(),
        },
        "targets": V3_TARGETS,
        "summary": {
            "ocr_rows": len(ocr_rows),
            "ocr_by_split": summarize(ocr_rows, "split"),
            "ocr_by_page_type": summarize(ocr_rows, "page_type"),
            "translation_rows": len(translation_rows),
            "translation_clean_rows_before_noise": before_noise,
            "translation_noise_rows_added": noise_added,
            "translation_by_split": summarize(translation_rows, "split"),
            "translation_by_input_kind": summarize(translation_rows, "input_kind"),
            "eval_rows": len(eval_rows),
            "eval_by_task": summarize(eval_rows, "task"),
        },
        "shortfalls": {
            split: max(0, target - Counter(row["split"] for row in ocr_rows).get(split, 0))
            for split, target in V3_TARGETS["ocr"].items()
        },
        "rejects": rejects,
        "policy": {
            "vulgate_drb": "disabled until verse alignment passes reference checks",
            "second_pass_failures": "eval_only_unless_corrected",
            "splits": "work_or_source_family_stable_hash",
            "primary_train_model": "Qwen3-VL-4B first; 8B only after dataset/eval gates pass",
        },
    }
    write_json(args.out / "manifest.json", manifest)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "v3")
    parser.add_argument("--max-ocr-pages", type=int, default=0, help="0 means no cap.")
    parser.add_argument("--min-ocr-alpha", type=int, default=20)
    parser.add_argument("--ocr-agreement-threshold", type=float, default=0.82)
    parser.add_argument("--min-release-faith", type=float, default=4.8)
    parser.add_argument("--max-external-classical", type=int, default=20000)
    parser.add_argument("--max-pair-chars", type=int, default=1800)
    parser.add_argument("--noise-source-limit", type=int, default=5000)
    args = parser.parse_args(argv)
    if args.max_ocr_pages == 0:
        args.max_ocr_pages = None
    return args


def main(argv: list[str] | None = None) -> int:
    manifest = build(parse_args(argv))
    print(json.dumps(manifest["summary"], ensure_ascii=False, indent=2))
    print(json.dumps({"shortfalls": manifest["shortfalls"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
