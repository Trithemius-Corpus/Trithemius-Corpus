"""Conservative reading-text cleanup for cipher and table-heavy T4B works.

Most works routed here cannot safely be flattened: page position is part of the
meaning of their alphabets, tables, sigils, or conjurations.  ``clean`` returns
``None`` for those works so the caller retains the segmented/diplomatic view.
The one prose work in the group receives only evidence-backed furniture removal
and unambiguous lowercase continuation joins.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


PROSE_WORK = "prdl-24357"

# These must retain page/segment structure until a table- and image-aware editor
# exists. Repetition in them can be cryptographic or ritual content.
SEGMENTED_WORKS = {
    "prdl-24389",  # Polygraphiae libri sex: cipher alphabets/tables
    "prdl-24391",  # Polygraphiae libri VI: cipher alphabets/tables/code fences
    "prdl-24395",  # Steganographia: conjurations and repeated formulae
    "prdl-70282",  # Clavis Polygraphiae: dense aligned alphabets/tables
    "prdl-70291",  # sigils: page-associated images and labels
    "prdl-70292",  # sigils: page-associated images and labels
}

_SEGMENT = re.compile(r"(?m)^\[segment \d+\]\s*$")
_PAGE = re.compile(r"(?m)^--- Page \d+ ---\s*$")

# Verified scan/catalogue furniture in the opening and closing leaves of 24357.
# Deliberately do not remove Roman numerals: most are genuine article numbers.
_24357_FURNITURE = re.compile(
    r"(?im)^(?:"
    r"Royal Library of Munich\.?|"
    r"Inc\. c\. a\. 158 8\. N 84\.3\.|"
    r"8� Inc\. c\. a\. 158 Heretica Hain 20|"
    r"6PW|"
    r"Inc\. c\. a\. 8� 158\. 1493|"
    r"No translatable text\.|"
    r"\[OCR-damaged non-body page; no recoverable connected text\.\]"
    r")\s*$"
)


def _work_key(work_id: str) -> str:
    """Accept either a bare PRDL id or a full work-directory slug."""
    match = re.match(r"(prdl-\d+)", work_id)
    return match.group(1) if match else work_id


def _clean_prose_24357(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = _SEGMENT.sub("", text)
    text = _24357_FURNITURE.sub("", text)

    # A page marker between a non-terminal phrase and a lowercase continuation
    # is an unambiguous physical-page interruption, not a paragraph boundary.
    # Optional short folio furniture has already been removed above.
    text = re.sub(
        r"([^.!?…:;\n])\n\n+--- Page \d+ ---\n\n+([a-z])",
        lambda m: f"{m.group(1)} {m.group(2)}",
        text,
    )
    text = _PAGE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def clean(work_id: str, text: str) -> str | None:
    """Return safe continuous Markdown, or ``None`` to retain segmentation."""
    key = _work_key(work_id)
    if key == PROSE_WORK:
        return _clean_prose_24357(text)
    if key in SEGMENTED_WORKS:
        return None
    return None


def _self_check(root: Path) -> None:
    prose_path = next((root / "works-t4b").glob("prdl-24357_*/english.md"))
    source = prose_path.read_text(encoding="utf-8")
    result = clean(prose_path.parent.name, source)
    assert result is not None
    assert "[segment " not in result
    assert not _PAGE.search(result)
    assert "Royal Library of Munich" not in result
    assert "Who Has Authority to Appoint Visitors of Monks" in result
    # Article numerals and italic headings are meaningful and must survive.
    assert "XXIII" in result
    assert "*Concerning visitors.*" in result

    for work in sorted(SEGMENTED_WORKS):
        path = next((root / "works-t4b").glob(f"{work}_*/english.md"))
        original = path.read_text(encoding="utf-8")
        assert clean(path.parent.name, original) is None

    source_words = len(re.findall(r"\b\w+\b", source))
    result_words = len(re.findall(r"\b\w+\b", result))
    retained = result_words / source_words
    assert retained > 0.99, retained
    print(
        f"24357: {source_words:,} -> {result_words:,} words "
        f"({retained:.2%} retained); 6 specialized works remain segmented."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        _self_check(Path(__file__).resolve().parents[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
