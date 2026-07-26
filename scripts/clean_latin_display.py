# -*- coding: utf-8 -*-
"""De-junk the committed Latin display artifacts (works/<id>/latin-ocr.txt).

Diplomatic cleanup: removes only non-text machine noise, never genuine Latin.
The rendered parallel viewer and the committed dataset then agree, and
``scripts/build_site.py`` stays a pure renderer.

What is removed
---------------
1. LEAKED STRUCTURAL XML — any ``<Tag ...>`` / ``</Tag>`` / ``<Tag .../>``
   left by the OCR/TEI pipeline. Text *between* tags is preserved (e.g. a
   drop-cap letter inside ``<Initial>C</Initial>`` stays as ``C``); only the
   markup itself is stripped. Garbled OCR'd tag names (``<Emphasisazarus``)
   are caught by the same general rule.
2. ENGLISH VISION/FIGURE DESCRIPTIONS — ``<description>…</description>`` and
   ``<Description …>…</Description>`` blocks hold English narration of the
   page image ("Manicule pointing hand…", "Broad horizontal band…"). The
   whole block is dropped; it is not Latin transcription.
3. LIBRARY CATALOG STAMPS — ``<Stamp description="…"/>`` self-closing tags
   (which encode "REGIA MONACENSIS" etc.) and the bare multi-line catalog
   blocks they mirror (``BIBLIOTHECA REGIA MONACENSIS``, ``Hain NNNNN``,
   ``Inc. c. a.``).
4. ENGLISH HALLUCINATION / MODEL CHATTER — explicit non-Latin phrases
   (biographical Wikipedia-style prose, "Royal Library of Monaco", assistant
   leaks, "Page intentionally blank"). Whole-segment replacement only when an
   explicit phrase fires; no word-density heuristics (those false-positive on
   cipher grids and library headers).
5. STRAY MARKDOWN — literal ``**Description:**`` and lone ``` fences.

Faithfulness guardrails
-----------------------
Never touches abbreviation glyphs (ꝺ ꝫ n̄ q̇ aͤ), never modernizes u/v/i/j,
never reflows hard line-wraps, never de-hyphenates, never merges or renumbers
segments. Idempotent.

Usage
-----
  python scripts/clean_latin_display.py             # dry-run report
  python scripts/clean_latin_display.py --apply     # write cleaned files
  python scripts/clean_latin_display.py --json      # machine-readable report
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKS = ROOT / "works"

SEGMENT_HEADER = re.compile(r"(?m)^\[segment\s+(\d+)\]\s*$")

# --- (1) leaked structural XML ---------------------------------------------
# Two treatments, by tag role:
#   (a) LINE/PARAGRAPH markers (Line, Paragraph, Heading, ...) carry the
#       printed line structure — the OCR pipeline emitted them IN PLACE OF the
#       newline (e.g. ``cir</Line>cūspecte`` is one word wrapped across two
#       printed lines). Replacing these tags with a newline preserves the
#       line breaks exactly and never merges distinct words.
#   (b) INLINE/semantic tags (Emphasis, Initial, Gap, Illegible, ...) wrap
#       text inline and are stripped to empty, KEEPING their text content
#       (a drop-cap letter, a damaged-gap marker's surrounding word).
# Garbled OCR'd tag names (``<Emphasisazarus``) fall through to (b). The inner
# span excludes newlines and is length-bounded so a stray ``<`` in genuine
# Latin is not mistaken for a tag.
LINE_MARKER_TAG = re.compile(
    r"</?(?:Line|Paragraph|Heading|line|p|li|Item|List|BlockQuotation|Blockquote|"
    r"Block-quote|Block quote|Block|Table|TableRow|tr|div|section|article|"
    r"Report|Document|Body|Page|Book|Volume|Manuscript|cc)\b[^\n<>]{0,120}?>",
    re.I,
)
ANGLE_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*\b[^\n<>]{0,120}?>")

# --- (2) English vision/figure description blocks --------------------------
# These wrap English narration of the page image, not Latin. Drop the whole
# block (tag + content). Case-insensitive on the tag name.
DESCRIPTION_BLOCK = re.compile(
    r"<(?:description|Description)\b[^<>]*>.*?</(?:description|Description)\s*",
    re.S | re.I,
)
# A lone unclosed <description> (OCR ate the closing tag): drop to end of line.
DESCRIPTION_LOOSE = re.compile(r"<(?:description|Description)\b[^<>]*>", re.I)

# --- (3) library catalog stamps --------------------------------------------
# Self-closing Stamp tags encode catalog stamps ("REGIA MONACENSIS").
STAMP_TAG = re.compile(r"<Stamp\b[^<>]*?/>", re.I)
# Bare multi-line catalog stamp lines (the human-readable mirror of <Stamp/>).
CATALOG_LINE = re.compile(
    r"""^\s*(?:
        BIBLIOTHECA\s+REGIA\s+MONACENSIS |
        Hain\s+\d{4,6} |
        J?nc\.\s*c\.\s*a\. |
        Inc\.\s*c\.\s*a\b |
        GW\s+M\d |
        BSB-Ink\b |
        Res/\d |
        4°\s+Inc\.\s*c\.\s*a
    )\s*$""",
    re.X | re.I,
)

# --- (4) English hallucination / model chatter -----------------------------
# Explicit, multi-word non-Latin phrases. Trusted without a density guard
# because each contains a signature that cannot occur in genuine Latin prose.
HALLUCINATION_PHRASE = re.compile(
    r"(?i)"
    r"Johannes\s+Trithemius\s+\(c\.\s*\d|"          # Wikipedia-style bio opener
    r"Royal\s+Library\s+of\s+Monaco|"               # catalogue hallucination
    r"Bibliotheca\s+Regia\s+Monacensis\s+refers\s+to|"
    r"If\s+your\s+query\s+pertains|"                # assistant leak
    r"please\s+let\s+me\s+know|"                    # assistant leak
    r"To\s+the\s+(?:left|right|center(?:re|er)?)\s+side\s+of|"  # vision layout
    r"\[Page\s+intentionally\s+blank\]|"
    r"No\s+clear\s+textual\s+content\s+can\s+be\s+discerned|"  # vision narration
    r"No\s+transcribed\s+content\s+(?:follows|is\s+present)|"
    r"String/Binding\s+Cord|"                       # binding description
    r"Faint\s+Text/Markings|"                       # margin reading
    r"appearing\s+to\s+read|"                       # vision narration
    r"\[Color\s+chart:|"                            # printed color reference
    r"adhering\s+strictly\s+to\s+instructions|"     # prompt leak
    r"This\s+description\s+focuses\s+solely|"
    r"The\s+image\s+(?:shows|displays|appears\s+to\s+be)|"
    r"provided\s+image\b|"
    r"I\s+(?:cannot|am\s+unable\s+to|will)\s+transcribe"
)

# --- (5) stray markdown -----------------------------------------------------
MARKDOWN_LEAK = re.compile(r"(?m)^\s*(?:```(?:plaintext)?\s*$|\*\*Description:\*\*\s*.*$)")


@dataclass
class Change:
    segment: int
    category: str
    before: str
    after: str


@dataclass
class FileReport:
    path: str
    changes: list[Change] = field(default_factory=list)


def _collapse_blank(lines: list[str]) -> list[str]:
    """Collapse 3+ blank lines to one blank line; strip leading blanks."""
    out: list[str] = []
    blanks = 0
    for ln in lines:
        if ln.strip() == "":
            blanks += 1
            if blanks <= 1:
                out.append("")
        else:
            blanks = 0
            out.append(ln)
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return out


def _drop_hallucination_paragraphs(body: str) -> tuple[str, bool]:
    """Remove English hallucination/model-chatter paragraphs, keep Latin.

    Operates at paragraph granularity (blocks separated by blank lines) so a
    segment that mixes a hallucinated bio with a genuine Latin incipit keeps
    the Latin. A paragraph is dropped only if it contains an explicit non-Latin
    signature phrase — never on word-density alone (that false-positives on
    cipher grids and library headers).
    """
    changed = False
    kept: list[str] = []
    # split on blank-line runs, preserving the separators
    for block in re.split(r"(\n\s*\n)", body):
        if block and HALLUCINATION_PHRASE.search(block):
            changed = True
            continue
        kept.append(block)
    return "".join(kept), changed


def clean_segment_body(body: str) -> tuple[str, list[str]]:
    """Return (cleaned_body, categories_applied). Diplomatic: keeps Latin."""
    applied: list[str] = []
    original = body

    # (2) drop English description blocks first (before generic tag strip)
    if DESCRIPTION_BLOCK.search(body):
        body = DESCRIPTION_BLOCK.sub("", body)
        applied.append("english-description-block")
    body = DESCRIPTION_LOOSE.sub("", body)

    # (3a) drop catalog Stamp self-closing tags
    if STAMP_TAG.search(body):
        body = STAMP_TAG.sub("", body)
        applied.append("catalog-stamp-tag")

    # (1) leaked structural XML:
    #     line/paragraph markers -> newline (preserve printed line structure);
    #     inline tags -> stripped, text kept.
    if LINE_MARKER_TAG.search(body):
        body = LINE_MARKER_TAG.sub("\n", body)
        applied.append("line-marker-tags")
    if ANGLE_TAG.search(body):
        body = ANGLE_TAG.sub("", body)
        applied.append("leaked-xml-tags")

    # (5) stray markdown
    if MARKDOWN_LEAK.search(body):
        body = MARKDOWN_LEAK.sub("", body)
        applied.append("markdown-leak")

    # (3b) drop bare catalog stamp lines (line-based, like strip_scan_boilerplate)
    kept = [ln for ln in body.splitlines() if not CATALOG_LINE.match(ln)]
    if len(kept) != len(body.splitlines()):
        applied.append("catalog-stamp-line")
    body = "\n".join(kept)

    # (4) drop English hallucination paragraphs (keep any Latin in the segment)
    body, hall_changed = _drop_hallucination_paragraphs(body)
    if hall_changed:
        applied.append("english-hallucination")

    # tidy whitespace introduced by removals
    body = "\n".join(_collapse_blank(body.splitlines()))

    # dedupe categories while preserving order
    seen: set[str] = set()
    applied = [c for c in applied if not (c in seen or seen.add(c))]
    if body.rstrip() == original.rstrip() and not applied:
        return original, []
    return body, applied


def clean_text(text: str) -> tuple[str, list[Change]]:
    """Clean a full latin-ocr.txt document, segment by segment."""
    changes: list[Change] = []
    matches = list(SEGMENT_HEADER.finditer(text))
    if not matches:
        # No segment markers: clean the whole thing as segment 1.
        cleaned, applied = clean_segment_body(text)
        if applied:
            changes.append(Change(1, ",".join(applied), text.strip(), cleaned.strip()))
        return cleaned, changes

    out: list[str] = []
    # preserve any leading content before the first header
    out.append(text[: matches[0].start()])
    for i, match in enumerate(matches):
        seg = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        header = match.group(0)
        body = text[start:end]
        cleaned, applied = clean_segment_body(body)
        if applied:
            changes.append(Change(seg, ",".join(applied), body.strip()[:200], cleaned.strip()[:200]))
        out.append(header.rstrip() + "\n")
        out.append(cleaned if cleaned.endswith("\n") else cleaned + "\n")
    new = "".join(out).rstrip("\n") + "\n"
    return new, changes


def build_report(apply: bool) -> list[FileReport]:
    reports: list[FileReport] = []
    for lf in sorted(glob.glob(str(WORKS / "*" / "latin-ocr.txt"))):
        p = Path(lf)
        orig = p.read_text(encoding="utf-8", errors="replace")
        new, changes = clean_text(orig)
        if changes:
            wid = p.parent.name
            reports.append(FileReport(path=str(p.relative_to(ROOT)), changes=changes))
            if apply:
                p.write_text(new, encoding="utf-8")
    return reports


def console_report(reports: list[FileReport]) -> str:
    total = sum(len(r.changes) for r in reports)
    cat_counts: dict[str, int] = {}
    for r in reports:
        for ch in r.changes:
            for cat in ch.category.split(","):
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
    lines = [
        f"files changed: {len(reports)} / 47",
        f"segments cleaned: {total}",
    ]
    for cat, n in sorted(cat_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {cat}: {n}")
    lines.append("")
    for r in sorted(reports, key=lambda x: -len(x.changes))[:15]:
        wid = Path(r.path).parent.name
        lines.append(f"  {wid}: {len(r.changes)} segment(s)")
        for ch in r.changes[:4]:
            safe_before = ch.before[:70].replace("\n", " ")
            lines.append(f"      seg {ch.segment} [{ch.category}]")
            if len(r.changes) > 4:
                break
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write cleaned files (default: dry-run)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON report")
    args = parser.parse_args()

    reports = build_report(apply=args.apply)
    if args.json:
        print(json.dumps([
            {"path": r.path, "changes": [c.__dict__ for c in r.changes]}
            for r in reports
        ], ensure_ascii=False, indent=2))
        return 0
    mode = "APPLIED" if args.apply else "DRY-RUN (no files written; re-run with --apply)"
    print(f"[{mode}]")
    print(console_report(reports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
