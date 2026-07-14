"""Conservative reading-text cleaners for devotional and homiletic T4B works.

The source ``english.md`` files are archival, page-faithful translations.  This
module removes scan/print furniture at display time and never rewrites them.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re


SUPPORTED = {"24376", "24385", "24393", "70283", "70285"}
PAGE_RE = re.compile(r"(?m)^--- Page (\d+) ---\s*$")

SKIP_PAGES = {
    "24376": set(range(1, 5)) | set(range(11, 15)),
    "24385": {1, 2, 3, 4, 5, 7, 9, 12},
    "24393": set(range(1, 8)) | set(range(156, 162)),
    "70283": {1, 2, 15, 16, 17, 18},
    "70285": {1, 2, 3, 4, 5} | set(range(200, 206)),
}

NON_BODY = re.compile(
    r"^(?:\[(?:Page\s+\d+|blank page|ocr-damaged non-body page[^]]*)\]|"
    r"(?:royal library(?: of munich)?|of munich|bavarian state library)\.?|"
    r"(?:kodak|gray scale)|<\d+|[A-Z]|\d+|[A-Z]\s+[ivx]+)$", re.I
)
RUNNING = re.compile(
    r"^(?:\*?)?(?:All Things\.\s*I\.|Folio\s+[IVXLCDM]+\.?)|"
    r"^(?:\*?)(?:Homily|Sermon)\s+[IVXLCDM]+\.?(?:\*?)$", re.I
)
HEADING = re.compile(
    r"^(?:Here (?:begins|ends)|Preface\b|Book (?:One|Two|I|II)\b|"
    r"On the (?:first|second|third|threefold|due|true|daily|knowledge|manner)\b|"
    r"How (?:the|carnal)\b|After (?:Matins|Vespers|celebration)\b|"
    r"At (?:Private Masses|Ite, missa est)\b|Consideration\s+[IVXLCDM]+\.?$|"
    r"Article\s+(?:\d+|[IVXLCDM]+)\.?$|Prayer\.?$|Another Prayer\.?)",
    re.I,
)


def _short_id(work_id: str) -> str | None:
    match = re.search(r"prdl-(\d+)", work_id)
    return match.group(1) if match and match.group(1) in SUPPORTED else None


def _paragraphs(raw: str) -> list[str]:
    raw = re.sub(r"(?m)^\[segment \d+\]\s*$", "", raw)
    return [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]


def _plain(paragraph: str) -> str:
    return " ".join(paragraph.replace("**", "").replace("*", "").split())


def _is_furniture(paragraph: str) -> bool:
    plain = _plain(paragraph)
    if NON_BODY.fullmatch(plain) or RUNNING.match(paragraph):
        return True
    if re.fullmatch(r"(?:\d+[ .]*){2,}", plain):
        return True
    if "digitalfoto-trainer.de" in plain or "Digitization Center" in plain:
        return True
    if plain.lower() in {"kodak gray scale", "herzog august bibliothek wolfenbüttel kodak gray scale"}:
        return True
    return False


def _heading(paragraph: str) -> str | None:
    plain = _plain(paragraph).strip()
    chapter_title = len(plain) <= 180 and re.search(
        r"\bChapter\s+(?:\d+|[IVXLCDM]+)\.?$", plain, re.I
    )
    if len(plain) > 180 or (not HEADING.match(plain) and not chapter_title):
        return None
    # End formulae remain prose; beginnings and descriptive labels navigate.
    if plain.lower().startswith("here ends"):
        return None
    return "### " + plain.rstrip(".")


def _ends_sentence(text: str) -> bool:
    return bool(re.search(r"[.!?;:][\"'’”)]?$", text.rstrip()))


def _catchword(previous: str, following: str) -> bool:
    word = _plain(previous).strip(" .,:;")
    nxt = _plain(following)
    if not word or len(word.split()) > 8 or len(word) > 70:
        return False
    return nxt.lower() == word.lower() or nxt.lower().startswith(word.lower() + " ")


def clean(work_id: str, text: str) -> str | None:
    """Return continuous Markdown for a supported work, else ``None``."""
    sid = _short_id(work_id)
    if sid is None:
        return None
    matches = list(PAGE_RE.finditer(text))
    if not matches:
        return None

    pages: list[tuple[int, list[str]]] = []
    for index, match in enumerate(matches):
        number = int(match.group(1))
        if number in SKIP_PAGES[sid]:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        paras = [p for p in _paragraphs(text[match.end():end]) if not _is_furniture(p)]
        if paras:
            pages.append((number, paras))

    # Printed sermon headings recur as running heads.  Keep their first real
    # occurrence, but discard later repetitions only when they head a page.
    counts = Counter(_plain(p) for _, ps in pages for p in ps)
    seen_headings: set[str] = set()
    output: list[str] = []
    for number, paras in pages:
        first = _plain(paras[0]) if paras else ""
        if sid == "24393" and counts[first] > 1 and (
            first.lower().startswith("on ") or "homily" in first.lower() or "sermon" in first.lower()
        ):
            if first in seen_headings:
                paras = paras[1:]
            else:
                seen_headings.add(first)
        if not paras:
            continue

        # Page turns commonly divide a sentence or duplicate a catchword.
        # The two verse works retain page-level stanza boundaries instead.
        if output and sid not in {"24376", "70283"}:
            if _catchword(output[-1], paras[0]):
                output.pop()
            elif not output[-1].startswith("#") and not _ends_sentence(output[-1]):
                output[-1] = output[-1].rstrip("-") + (
                    "" if output[-1].endswith("-") else " "
                ) + paras.pop(0).lstrip(".… ")

        for paragraph in paras:
            marked = _heading(paragraph)
            if marked:
                output.append(marked)
            elif sid == "24376" and number in range(6, 11) and "\n" in paragraph:
                # Hucbald's alliterative poem must retain its translated lines.
                output.append("  \n".join(line.strip() for line in paragraph.splitlines()))
            else:
                output.append(paragraph)

    return re.sub(r"\n{3,}", "\n\n", "\n\n".join(output)).strip()


def _self_check(root: Path) -> None:
    for sid in sorted(SUPPORTED):
        source = next((root / "works-t4b").glob(f"prdl-{sid}_*/english.md"))
        original = source.read_text(encoding="utf-8")
        result = clean(source.parent.name, original)
        assert result and len(result) > 1000, sid
        assert "--- Page " not in result and "[segment " not in result, sid
        assert "[blank page]" not in result.lower(), sid
        if sid == "70283":
            assert result.count("Hail.") >= 35  # genuine litany/refrain
        if sid == "24376":
            assert result.count("Clear-sounding Muses") >= 5
        print(sid, f"{len(original):,} -> {len(result):,} chars", f"{result.count(chr(10)+chr(10))+1:,} blocks")


if __name__ == "__main__":
    _self_check(Path(__file__).resolve().parents[1])
