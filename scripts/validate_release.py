"""Read-only public release validator for the Trithemius Corpus.

This script checks that the committed release artifacts agree with each other:
manifest, per-work metadata, quality ledgers, docs, static site links, search
assets, and common local-junk patterns. It never rewrites files.
"""
from __future__ import annotations

import csv
import html as html_lib
import html.parser
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
WORKS = ROOT / "works"
SITE = ROOT / "site" / "dist"
QUALITY = ROOT / "data" / "_quality"
PUBLIC_RELEASE_LEDGER = QUALITY / "public_release_chunks.jsonl"
PUBLIC_SELECTION_HISTORY = QUALITY / "public_selection_history.jsonl"

EXPECTED_TRANS_WORKS = 47
EXPECTED_SKIPPED = 4
EXPECTED_CHUNKS_TOTAL = 4400
EXPECTED_CHUNKS_GRADED = 4353
EXPECTED_TIERS = {"S": 47, "A": 0, "B": 0, "C": 0, "F": 0}

JUNK_PATHS = [
    "scripts/_cp_audit",
    "scripts/_chrome_profile_measure",
    "scripts/_shots",
    "site/dist/works/nul",
    "site/dist/model-comparison.html",
    "site/dist/npu-translation-issues.html",
    "AUDIT_REVIEW_FACTCHECK_2026-06-19.md",
    "CLAUDE_VISION_REOCR_TEST.md",
    "_rename_map.json",
    "_unclear_proposals_prdl-24390.json",
    "_unclear_proposals_prdl-70280.json",
]

JUNK_GLOBS = [
    "site/dist/_REVIEW*.md",
    "works/**/*.pre184",
    "works/**/*.preintro",
    "works/**/*.stub",
]

STALE_PATTERNS = {
    "mainz-1494": "prdl-70283 should use the Liptzk/HAB 1501 slug",
    "Sancctissime": "70283 title typo should not survive in release text",
    "LIMITATIONS.md": "LIMITATIONS.md was folded into METHODOLOGY.md",
    "PIPELINE.md": "PIPELINE.md was folded into METHODOLOGY.md",
    "S=31 / A=12 / B=2 / C=2": "old quality distribution in release-facing file",
    "3,666 chunks": "old quality chunk count in release-facing file",
    "9.3% of chunks flagged": "old hallucination headline in release-facing file",
}

RELEASE_FACING_TEXT = [
    "README.md",
    "CONTRIBUTING.md",
    "CITATION.cff",
    ".zenodo.json",
    "docs/RELEASE_CHECKLIST.md",
    "data/_quality/scoreboard_gpt_v3.md",
]

# Private-pipeline / operator leak signatures that must never reach a reader page
# or a rendered source file (intro.md, ERRATA.md). These are working-corpus paths
# and pipeline lane names that have nothing to do with the published scholarship.
# A green validator while these were live on two work pages is exactly the gap the
# 2026-06-26 audit (F1/F3) found, so this check closes it.
LEAK_PATTERNS = [
    (re.compile(r"[A-Za-z]:\\"), "absolute Windows path"),
    (re.compile(r"(?i)\bAppData\b"), "AppData path"),
    (re.compile(r"file:///"), "local file:// URL"),
    (re.compile(r"Output written to"), "operator output note"),
    (re.compile(r"_zoom"), "zoom-crop working dir"),
    (re.compile(r"_public_pre"), "private pre-fold lane dir"),
    (re.compile(r"public_prefold"), "private prefold lane dir"),
    (re.compile(r"codex-sweep"), "pipeline lane name"),
    (re.compile(r"fable5_grades"), "internal grade ledger"),
    (re.compile(r"grade_fable5_pass"), "internal grader script"),
    (re.compile(r"to seed reviewer"), "reviewer-seed note"),
]

VISION_NARRATION_PATTERNS = [
    (re.compile(r"(?i)\bGiven that\b.*\b(?:image|page|transcribe|provided)\b"), "vision-model narration"),
    (re.compile(r"(?i)\bI (?:cannot|am unable to) transcribe\b"), "vision-model refusal/narration"),
    (re.compile(r"(?i)\bplease let me know\b"), "assistant conversational leak"),
    (re.compile(r"(?i)\bprovided image\b"), "vision-model image description"),
    (re.compile(r"(?i)\bThe image (?:provided|shows|displays)\b"), "vision-model image description"),
    (re.compile(r"(?i)\bThis page serves as the frontispiece\b"), "vision-model image description"),
    (re.compile(r"(?i)\bNo textual content is present\b"), "vision-model no-content narration"),
    (re.compile(r"(?i)\bThis description focuses solely\b"), "vision-model image description"),
    (re.compile(r"(?i)\bDescription: Positioned over\b"), "vision-model figure description"),
    (re.compile(r"(?im)^\s*Description:\s+"), "vision-model figure description"),
    (re.compile(r"(?i)\badhering strictly to instructions\b"), "prompt/instruction leak"),
    (re.compile(r"(?i)\bNo transcribed content follows\b"), "vision-model no-content narration"),
]

PARALLEL_SOURCE_PLACEHOLDERS = {
    "",
    "[illegible]",
    "[blank]",
    "[non-text scan boilerplate removed]",
}

GRADE_FIELDS = [
    "record", "translation_backend", "grader", "raw_faith", "adj_faith",
    "raw_fluent", "adj_fluent", "hallucinated", "preamble", "refusal", "notes",
]


@dataclass
class Result:
    errors: list[str]
    warnings: list[str]

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.links.append((name, value))


def strip_html_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def iter_parallel_segments(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return
    block_re = re.compile(
        r'<div class="pp-n" id="seg-(\d+)".*?'
        r'(?=<div class="pp-n" id="seg-\d+"|</div>\s*<div class="pp-seg-indicator")',
        re.S,
    )
    for match in block_re.finditer(text):
        block = match.group(0)
        latin_match = re.search(
            r'<div class="pp-latin"[^>]*>(.*?)</div>\s*<div class="pp-english',
            block,
            re.S,
        )
        english_match = re.search(
            r'<div class="pp-english[^"]*">(.*)</div>\s*$',
            block,
            re.S,
        )
        yield (
            int(match.group(1)),
            strip_html_text(latin_match.group(1)) if latin_match else "",
            strip_html_text(english_match.group(1)) if english_match else "",
        )


def load_json(path: Path, result: Result) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        result.error(f"{path.relative_to(ROOT)} is not valid JSON: {exc}")
        return None


def is_true(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def validate_yaml_cff(result: Result) -> None:
    path = ROOT / "CITATION.cff"
    try:
        import yaml  # type: ignore
    except Exception:
        result.warn("PyYAML not installed; skipped full CITATION.cff YAML parse")
        return
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        result.error(f"CITATION.cff is not valid YAML: {exc}")


def validate_manifest(result: Result) -> dict:
    manifest = load_json(ROOT / "manifest.json", result)
    if not isinstance(manifest, dict):
        return {}

    works = manifest.get("works")
    if not isinstance(works, list):
        result.error("manifest.json does not contain a works list")
        return {}

    translated = [w for w in works if not w.get("skip")]
    skipped = [w for w in works if w.get("skip")]
    if manifest.get("translatable_works") != EXPECTED_TRANS_WORKS or len(translated) != EXPECTED_TRANS_WORKS:
        result.error(f"manifest translatable works should be {EXPECTED_TRANS_WORKS}, got header={manifest.get('translatable_works')} rows={len(translated)}")
    if manifest.get("skipped_works") != EXPECTED_SKIPPED or len(skipped) != EXPECTED_SKIPPED:
        result.error(f"manifest skipped works should be {EXPECTED_SKIPPED}, got header={manifest.get('skipped_works')} rows={len(skipped)}")

    tier_counts = {k: 0 for k in EXPECTED_TIERS}
    total = 0
    graded = 0
    seen: set[str] = set()
    for w in translated:
        wid = w.get("id")
        if not isinstance(wid, str):
            result.error("manifest work without string id")
            continue
        if wid in seen:
            result.error(f"duplicate manifest id: {wid}")
        seen.add(wid)
        tier = w.get("tier")
        if tier in tier_counts:
            tier_counts[tier] += 1
        else:
            result.error(f"{wid}: invalid tier {tier!r}")
        faith = float(w.get("faithful_adj") or 0)
        hall = float(w.get("hallucinated_pct") or 0)
        chunks_total = int(w.get("chunks_total") or 0)
        chunks_graded = int(w.get("chunks_graded") or 0)
        coverage = float(w.get("coverage_pct") or 0)
        total += chunks_total
        graded += chunks_graded
        if tier != "S" or faith < 4.0 or hall != 0.0:
            result.error(f"{wid}: release work is not all-S clean (tier={tier}, faith={faith}, hall={hall})")
        if chunks_graded > chunks_total:
            result.error(f"{wid}: chunks_graded {chunks_graded} exceeds chunks_total {chunks_total}")
        if not (0.0 <= coverage <= 100.0):
            result.error(f"{wid}: coverage_pct out of range: {coverage}")
    if tier_counts != EXPECTED_TIERS:
        result.error(f"tier distribution should be {EXPECTED_TIERS}, got {tier_counts}")
    if total != EXPECTED_CHUNKS_TOTAL or graded != EXPECTED_CHUNKS_GRADED:
        result.error(f"chunk totals should be total={EXPECTED_CHUNKS_TOTAL}, graded={EXPECTED_CHUNKS_GRADED}; got total={total}, graded={graded}")
    return {w["id"]: w for w in translated if isinstance(w.get("id"), str)}


def validate_work_artifacts(manifest_by_id: dict, result: Result) -> None:
    metadata_paths = sorted(WORKS.glob("prdl-*/metadata.json"))
    metadata_ids = {p.parent.name for p in metadata_paths}
    manifest_ids = set(manifest_by_id)
    if metadata_ids != manifest_ids:
        result.error(f"work metadata ids differ from manifest: missing={sorted(manifest_ids - metadata_ids)[:5]} extra={sorted(metadata_ids - manifest_ids)[:5]}")

    for wid, manifest_work in sorted(manifest_by_id.items()):
        work_dir = WORKS / wid
        required = ["english.md", "latin-ocr.txt", "intro.md", "metadata.json", "chapters.json", "ERRATA.md", "chunks/grades.csv"]
        for rel in required:
            if not (work_dir / rel).exists():
                result.error(f"{wid}: missing {rel}")
        metadata = load_json(work_dir / "metadata.json", result)
        if not isinstance(metadata, dict):
            continue
        if metadata.get("id") != wid:
            result.error(f"{wid}: metadata id mismatch {metadata.get('id')!r}")
        for key in ["title", "year", "source_year", "edition_info", "tier", "faithful_adj", "chunks_graded", "chunks_total", "coverage_pct", "hallucinated_pct"]:
            if metadata.get(key) != manifest_work.get(key):
                result.error(f"{wid}: metadata {key}={metadata.get(key)!r} differs from manifest {manifest_work.get(key)!r}")
        chunk_files = list((work_dir / "chunks").glob("full_chunk_*.md"))
        chunk_names = {p.name for p in chunk_files}
        if len(chunk_files) > int(metadata.get("chunks_total") or 0):
            result.error(f"{wid}: {len(chunk_files)} chunk files exceeds chunks_total {metadata.get('chunks_total')}")
        if len(chunk_files) < int(metadata.get("chunks_total") or 0):
            result.error(f"{wid}: only {len(chunk_files)} chunk files on disk but chunks_total is {metadata.get('chunks_total')}")
        missing_nums = [i for i in range(1, int(metadata.get("chunks_total") or 0) + 1)
                        if f"full_chunk_{i:04d}.md" not in chunk_names]
        if missing_nums:
            result.error(f"{wid}: chunk numbering has gaps vs chunks_total: {missing_nums[:8]}"
                         + ("..." if len(missing_nums) > 8 else ""))
        chapters_path = work_dir / "chapters.json"
        if chapters_path.exists():
            chapters = load_json(chapters_path, result)
            if isinstance(chapters, dict):
                for entry in chapters.get("entries") or []:
                    n = entry.get("n") if isinstance(entry, dict) else None
                    if isinstance(n, int) and f"full_chunk_{n:04d}.md" not in chunk_names:
                        result.error(f"{wid}: chapters.json anchor n={n} ({entry.get('label','?')}) has no chunk file")
        if metadata.get("license") != "CC0-1.0":
            result.error(f"{wid}: metadata license should be CC0-1.0")
        viewer = ((metadata.get("artifacts") or {}).get("parallel_viewer") or "")
        if wid not in viewer:
            result.error(f"{wid}: parallel_viewer does not reference current id")

        grades_path = work_dir / "chunks" / "grades.csv"
        try:
            with grades_path.open(encoding="utf-8-sig", newline="") as fh:
                grade_rows = list(csv.DictReader(fh))
        except Exception as exc:  # noqa: BLE001
            result.error(f"{wid}: chunks/grades.csv cannot be read: {exc}")
            continue
        public_rows = [r for r in grade_rows if r.get("translation_backend") == "public"]
        expected_public = int(manifest_work.get("chunks_graded") or 0)
        if len(public_rows) != expected_public:
            result.error(f"{wid}: public grade rows should be {expected_public}, got {len(public_rows)}")
        public_records = [r.get("record", "") for r in public_rows]
        if len(public_records) != len(set(public_records)):
            result.error(f"{wid}: duplicate public grade records")
        for rec in public_records:
            if rec and f"{rec}.md" not in chunk_names:
                result.error(f"{wid}: graded record {rec} has no chunk file on disk")
        for row in public_rows:
            record = row.get("record") or "<missing record>"
            if to_float(row.get("adj_faith")) < 4.0:
                result.error(f"{wid} {record}: public adj_faith below S threshold")
            for flag in ["hallucinated", "preamble", "refusal"]:
                if is_true(row.get(flag)):
                    result.error(f"{wid} {record}: public {flag}=True")
        if public_rows:
            mean_faith = sum(to_float(r.get("adj_faith")) for r in public_rows) / len(public_rows)
            if abs(mean_faith - float(manifest_work.get("faithful_adj") or 0.0)) > 0.011:
                result.error(f"{wid}: public grade mean {mean_faith:.2f} differs from manifest faithful_adj {manifest_work.get('faithful_adj')}")


def validate_quality(manifest_by_id: dict, result: Result) -> None:
    csv_path = QUALITY / "scoreboard_gpt_v3.csv"
    md_path = QUALITY / "scoreboard_gpt_v3.md"
    summary_path = QUALITY / "gpt55_v3_canonical.summary.json"
    rows = []
    try:
        with csv_path.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except Exception as exc:  # noqa: BLE001
        result.error(f"{csv_path.relative_to(ROOT)} cannot be read: {exc}")
    if len(rows) != EXPECTED_TRANS_WORKS:
        result.error(f"scoreboard CSV should have {EXPECTED_TRANS_WORKS} rows, got {len(rows)}")
    row_by_id = {row.get("work_id", ""): row for row in rows}
    if set(row_by_id) != set(manifest_by_id):
        result.error("scoreboard CSV work ids differ from manifest ids")
    if any(row.get("honest_tier") != "S" for row in rows):
        result.error("scoreboard CSV contains non-S honest_tier rows")
    n_sum = sum(int(float(row.get("n") or 0)) for row in rows)
    if n_sum != EXPECTED_CHUNKS_GRADED:
        result.error(f"scoreboard CSV n sum should be {EXPECTED_CHUNKS_GRADED}, got {n_sum}")
    for wid, manifest_work in sorted(manifest_by_id.items()):
        row = row_by_id.get(wid)
        if not row:
            continue
        if int(float(row.get("n") or 0)) != int(manifest_work.get("chunks_graded") or 0):
            result.error(f"{wid}: scoreboard n differs from manifest chunks_graded")
        if abs(to_float(row.get("faith_gpt")) - float(manifest_work.get("faithful_adj") or 0.0)) > 0.011:
            result.error(f"{wid}: scoreboard faith_gpt differs from manifest faithful_adj")
        if to_float(row.get("hall_pct")) != float(manifest_work.get("hallucinated_pct") or 0.0):
            result.error(f"{wid}: scoreboard hall_pct differs from manifest hallucinated_pct")
    md = md_path.read_text(encoding="utf-8", errors="replace") if md_path.exists() else ""
    for needle in ["S=47", "4,400", "4,353", "0.0%"]:
        if needle not in md:
            result.error(f"scoreboard markdown missing {needle!r}")
    summary = load_json(summary_path, result)
    if isinstance(summary, dict):
        if summary.get("published_chunks_total") != EXPECTED_CHUNKS_TOTAL:
            result.error("quality summary published_chunks_total mismatch")
        if summary.get("published_chunks_graded") != EXPECTED_CHUNKS_GRADED:
            result.error("quality summary published_chunks_graded mismatch")
        if summary.get("tier_distribution", {}).get("S") != EXPECTED_TRANS_WORKS:
            result.error("quality summary tier_distribution mismatch")

    release_rows: list[dict] = []
    try:
        with PUBLIC_RELEASE_LEDGER.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    result.error(f"{PUBLIC_RELEASE_LEDGER.relative_to(ROOT)}:{lineno}: row is not an object")
                    continue
                release_rows.append(row)
    except Exception as exc:  # noqa: BLE001
        result.error(f"{PUBLIC_RELEASE_LEDGER.relative_to(ROOT)} cannot be read: {exc}")
    if len(release_rows) != EXPECTED_CHUNKS_GRADED:
        result.error(f"public release chunk ledger should have {EXPECTED_CHUNKS_GRADED} rows, got {len(release_rows)}")
    ledger_counts: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for row in release_rows:
        wid = str(row.get("work_id") or "")
        record = str(row.get("record") or "")
        ledger_counts[wid] = ledger_counts.get(wid, 0) + 1
        key = (wid, record)
        if key in seen:
            result.error(f"duplicate public release ledger row: {wid} {record}")
        seen.add(key)
        if row.get("translation_backend") != "public":
            result.error(f"{wid} {record}: release ledger backend is not public")
        if wid not in manifest_by_id:
            result.error(f"{wid} {record}: release ledger work id is not in manifest")
        if to_float(row.get("adj_faith")) < 4.0:
            result.error(f"{wid} {record}: release ledger adj_faith below S threshold")
        for flag in ["hallucinated", "preamble", "refusal"]:
            if is_true(row.get(flag)):
                result.error(f"{wid} {record}: release ledger {flag}=True")
    for wid, manifest_work in sorted(manifest_by_id.items()):
        if ledger_counts.get(wid, 0) != int(manifest_work.get("chunks_graded") or 0):
            result.error(f"{wid}: release ledger count {ledger_counts.get(wid, 0)} differs from manifest chunks_graded")


def validate_docs(result: Result) -> None:
    for rel in RELEASE_FACING_TEXT:
        path = ROOT / rel
        if not path.exists():
            result.error(f"release-facing file missing: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle, explanation in STALE_PATTERNS.items():
            if needle in text:
                result.error(f"{rel}: stale pattern {needle!r} ({explanation})")
        if "XXXXXXX" in text:
            result.warn(f"{rel}: unresolved Zenodo DOI placeholder 'XXXXXXX' - replace once the DOI is minted")

    if (QUALITY / "public_selection.jsonl").exists():
        result.error("data/_quality/public_selection.jsonl should be renamed to public_selection_history.jsonl")
    if not PUBLIC_SELECTION_HISTORY.exists():
        result.error("data/_quality/public_selection_history.jsonl is missing")
    readme = QUALITY / "README.md"
    if not readme.exists():
        result.error("data/_quality/README.md is missing")
    else:
        text = readme.read_text(encoding="utf-8", errors="replace")
        for needle in ["public_release_chunks.jsonl", "public_selection_history.jsonl", "Current release evidence"]:
            if needle not in text:
                result.error(f"data/_quality/README.md missing {needle!r}")


def validate_source_sanity(result: Result) -> None:
    checks = {
        "prdl-24368_de-operatione-divini-amoris": [
            "historia plantarum",
            "Alictea",
            "Amaryllidis",
            "Asparagus",
        ],
    }
    for wid, forbidden in checks.items():
        path = WORKS / wid / "latin-ocr.txt"
        if not path.exists():
            result.error(f"{wid}: missing latin-ocr.txt for source sanity check")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        for needle in forbidden:
            if needle.lower() in lower:
                result.error(f"{wid}: wrong-source signature remains in latin-ocr.txt: {needle!r}")
        if "[segment 2]\n[Source page illegible in the scan; the page image is the authoritative witness.]" not in text:
            result.error(f"{wid}: segment 2 should be the source-page-illegible witness note")


def validate_bibliographic_fixes(manifest_by_id: dict, result: Result) -> None:
    if any("mainz-1494" in wid for wid in manifest_by_id):
        result.error("prdl-70283 still uses mainz-1494 slug")
    expected_70283 = "prdl-70283_de-laudibus-sanctissimae-matris-annae-liptzk-1501-hab"
    if expected_70283 not in manifest_by_id:
        result.error(f"missing corrected 70283 id {expected_70283}")
    poly = manifest_by_id.get("prdl-24390_polygraphiae-libri-vi", {})
    if "Basel" not in str(poly.get("edition_info")) or "Furter" not in str(poly.get("edition_info")):
        result.error("prdl-24390 edition_info should identify Basel / Furter-Petri / Haselberg")
    if "[Oppenheim]" in str(poly.get("edition_info")):
        result.error("prdl-24390 edition_info still presents Oppenheim as current attribution")


def validate_junk(result: Result) -> None:
    for rel in JUNK_PATHS:
        path = ROOT / rel
        if rel.endswith("/nul") and not path.is_file():
            continue
        if path.exists():
            result.error(f"local release junk still exists: {rel}")
    for pattern in JUNK_GLOBS:
        matches = list(ROOT.glob(pattern))
        if matches:
            preview = ", ".join(str(m.relative_to(ROOT)) for m in matches[:5])
            result.error(f"junk pattern {pattern!r} matched {len(matches)} files: {preview}")


def should_skip_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https", "mailto", "tel", "javascript", "data"}:
        return True
    if url.startswith("#") or not url.strip():
        return True
    return False


def validate_site_links(result: Result) -> None:
    if not SITE.exists():
        result.error("site/dist is missing")
        return
    for rel in ["search.html", "pagefind/pagefind.js", "pagefind/pagefind-ui.js", "pagefind/pagefind-entry.json"]:
        if not (SITE / rel).exists():
            result.error(f"search asset missing: site/dist/{rel}")

    html_files = sorted(SITE.rglob("*.html"))
    if not html_files:
        result.error("site/dist contains no HTML files")
    for html_file in html_files:
        parser = LinkParser()
        try:
            parser.feed(html_file.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            result.error(f"{html_file.relative_to(ROOT)} could not be parsed for links: {exc}")
            continue
        for attr, url in parser.links:
            if should_skip_url(url):
                continue
            clean = unquote(url.split("#", 1)[0].split("?", 1)[0])
            if not clean or clean.startswith("/"):
                continue
            target = (html_file.parent / clean).resolve()
            try:
                target.relative_to(SITE.resolve())
            except ValueError:
                result.error(f"{html_file.relative_to(ROOT)} {attr} points outside site/dist: {url}")
                continue
            if not target.exists():
                result.error(f"{html_file.relative_to(ROOT)} has broken local {attr}: {url}")


def _scan_for_leaks(text: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for pattern, label in LEAK_PATTERNS:
            if pattern.search(line):
                hits.append((lineno, label))
    return hits


def validate_no_leaks(result: Result) -> None:
    """Fail if any reader-facing rendered page or rendered source file (intro.md,
    ERRATA.md) exposes a working-corpus path or pipeline lane name."""
    targets: list[Path] = []
    if SITE.exists():
        targets += [p for p in SITE.rglob("*.html") if "pagefind" not in p.parts]
    targets += sorted(WORKS.glob("prdl-*/ERRATA.md"))
    targets += sorted(WORKS.glob("prdl-*/intro.md"))
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            result.error(f"{path.relative_to(ROOT)} could not be read for leak scan: {exc}")
            continue
        for lineno, label in _scan_for_leaks(text):
            result.error(f"{path.relative_to(ROOT)}:{lineno}: private leak ({label})")


def validate_no_ocr_narration(result: Result) -> None:
    """Fail on OCR/vision-model prose that leaked into Latin source artifacts or
    rendered public pages. These are not transcriptions; they are model chatter."""
    targets: list[Path] = sorted(WORKS.glob("prdl-*/latin-ocr.txt"))
    if SITE.exists():
        targets += [p for p in SITE.rglob("*.html") if "pagefind" not in p.parts]
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            result.error(f"{path.relative_to(ROOT)} could not be read for OCR narration scan: {exc}")
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern, label in VISION_NARRATION_PATTERNS:
                if pattern.search(line):
                    result.error(f"{path.relative_to(ROOT)}:{lineno}: {label}")


def validate_parallel_evidence(result: Result) -> None:
    """A parallel viewer must not present long English against a placeholder
    Latin source. That makes the public evidence layer unverifiable."""
    if not SITE.exists():
        return
    for path in sorted((SITE / "works").glob("*_parallel.html")):
        for seg, latin, english in iter_parallel_segments(path):
            latin_norm = latin.strip()
            english_norm = english.strip()
            if latin_norm in PARALLEL_SOURCE_PLACEHOLDERS and len(english_norm) > 500:
                result.error(
                    f"{path.relative_to(ROOT)}#seg-{seg}: placeholder Latin "
                    f"({latin_norm or 'empty'}) paired with {len(english_norm)} chars of English"
                )


def validate_frontend_runtime(result: Result) -> None:
    """Catch generated JavaScript that browsers reject at runtime."""
    if not SITE.exists():
        return
    invalid_root_margin = re.compile(r"rootMargin\s*:\s*['\"][^'\"]*\b(?:rem|em|vh|vw)\b", re.I)
    for path in sorted(SITE.rglob("*.html")):
        if "pagefind" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            result.error(f"{path.relative_to(ROOT)} could not be read for frontend scan: {exc}")
            continue
        if invalid_root_margin.search(text):
            result.error(
                f"{path.relative_to(ROOT)}: IntersectionObserver rootMargin uses "
                "CSS units unsupported by the browser API"
            )


def validate_search_freshness(result: Result) -> None:
    """Warn (not fail) if the Pagefind index is older than the rendered HTML, i.e.
    site search is stale relative to the pages it indexes."""
    if not SITE.exists():
        return
    pagefind_js = SITE / "pagefind" / "pagefind.js"
    if not pagefind_js.exists():
        return
    index_mtime = pagefind_js.stat().st_mtime
    newer = [
        p for p in SITE.rglob("*.html")
        if "pagefind" not in p.parts and "editions" not in p.parts
        and p.stat().st_mtime > index_mtime + 1
    ]
    if newer:
        example = newer[0].relative_to(ROOT)
        result.warn(
            f"Pagefind index is older than {len(newer)} rendered HTML file(s); "
            f"run `npx pagefind --site site/dist` before deploy (e.g. {example})"
        )


def main() -> int:
    result = Result(errors=[], warnings=[])
    validate_yaml_cff(result)
    manifest_by_id = validate_manifest(result)
    validate_work_artifacts(manifest_by_id, result)
    validate_quality(manifest_by_id, result)
    validate_docs(result)
    validate_source_sanity(result)
    validate_bibliographic_fixes(manifest_by_id, result)
    validate_junk(result)
    validate_site_links(result)
    validate_no_leaks(result)
    validate_no_ocr_narration(result)
    validate_parallel_evidence(result)
    validate_frontend_runtime(result)
    validate_search_freshness(result)

    for warning in result.warnings:
        print(f"WARN: {warning}")
    if result.errors:
        print("Release validation failed:")
        for error in result.errors:
            print(f"  - {error}")
        return 1
    print("Release validation passed.")
    print(f"  works: {EXPECTED_TRANS_WORKS} translatable + {EXPECTED_SKIPPED} skipped")
    print(f"  chunks: {EXPECTED_CHUNKS_TOTAL} total / {EXPECTED_CHUNKS_GRADED} graded")
    print("  historical machine-audit manifest: 47/47 formerly labeled S; retained for provenance only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
