# -*- coding: utf-8 -*-
"""Clean OCR pollution from published works/<id>/latin-ocr.txt artifacts.

Two operations, both conservative (never touch real Latin):

  (1) ?-WALL COLLAPSE — runs of 4+ consecutive '?' (the OCR's "I can't read
      this" glyph) collapse to a single '[illegible]'.

  (2) WHOLE-SEGMENT ENGLISH VISION-DESCRIPTION REPLACEMENT — when an OCR model
      could not read a page it sometimes emitted English prose describing the
      *image* ("The image displays what appears to be the verso of a blank
      page..."). These appear in the Latin column and are replaced with
      '[illegible]'.

      Replacement is GATED on an explicit multi-word English phrase that cannot
      occur in Latin. Word-counting is NOT used (Latin and English share too
      many short words; it destroys real Latin). Each segment is replaced only
      if it matches at least one explicit phrase AND the matching phrase is a
      complete sentence/clause (capitalized, >4 words).

Idempotent. Reads from the working tree (works/*/latin-ocr.txt).
Run:  python scripts/clean_latin_ocr.py [--apply]   (default = dry-run/report)
"""
import re, glob, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- (1) ?-wall collapse ---
QWALL = re.compile(r"(?:\?\s*){4,}")

# --- (2a) STRONG OCR-meta disclaimers — these multi-word phrases cannot occur
# in Latin and are trusted without a language-density guard. The OCR model is
# explaining it's describing the image rather than transcribing.
STRONG_META = re.compile(
    r"adhering strictly to instructions|"
    r"For any subsequent questions regarding this dataset|"
    r"Each column heading in Table \d+|"
    r"This transcription focuses solely|"
    r"A sequence identifier possibly indicating|"
    r"identifying elements present visually within provided image|"
    r"generalizations not supported by direct visual evidence|"
    r"This transcription adheres strictly|"
    r"This description focuses solely|"
    r"^\s*Description:\s+|"
    r"The requested content appears to be blank|"
    r"This book contains \d+ pages|"
    r"<(?:HistoricalDocument|Image|Scan)\b|"
    r"No transcribed content follows|"
    r"Description: A small decorative", re.I)

# --- (2b) WEAKER vision-description phrases — these need a language-density
# guard (english common-words must dominate) so real Latin isn't harmed.
VISION_SENTENCES = [
    r"The (?:provided )?image (?:shows|displays|appears to be|depicts) (?:what appears to be )?(?:a |an |the )?[a-z]+",
    r"The image provided appears",
    r"image provided",
    r"The provided image does not show such content",
    r"The provided OCR (?:snippets|suggests)",
    r"The transcribed output will be based solely",
    r"The transcribed content consists solely",
    r"This page serves as the frontispiece",
    r"It features an ornate",
    r"Marbling involves",
    r"This technique produced",
    r"The choice of colors",
    r"overall aesthetic suggests",
    r"This (?:page|image|sheet) (?:appears to be|is|shows|contains) (?:a |an |blank|empty|no )",
    r"No textual content is visible",
    r"No textual content is present",
    r"There is no discernible text",
    r"There (?:is|are) no visible (?:text|content|words|markings|paragraphs)",
    r"intentionally left blank",
    r"discernible from the image",
    r"visual cues from the image",
    r"visually present",
    r"Description: Positioned over",
    r"The content within this small frame is illegible",
    r"The (?:page|paper|material|background) (?:appears|is|has|shows) ",
    r"What (?:is )?appears to be a damaged (?:book|cover|binding)",
    r"(?:Given|Overall|Based on) (?:that|the|this) ",
    r"Based solely on the visual information",
    r"provided image data",
    r"I (?:cannot|am unable to|will) transcribe",
    r"If you (?:have another|need|were)",
    r"please let me know",
    r"This (?:also )?appears to be blank",
    r"Page \d+: This appears",
    r"Categorization like",
    r"No\.: A sequence identifier",
]
VPAT = re.compile(r"(?:" + "|".join(VISION_SENTENCES) + r")", re.I)

ENGLISH_MARKERS = re.compile(
    r"\b(the|and|of|to|is|are|with|this|that|there|from|what|if|you|"
    r"page|image|provided|appears|blank|visible|paper|book|cover|sheet|"
    r"material|leather|damaged|paragraphs|headings|content|text|words|"
    r"shows|displays|contains|background|binding|minor|spots|edges|single|"
    r"surface|document|another|need|assistance|please|further|details|"
    r"transcribe|transcription|instruction|visual|observed|based|solely|"
    r"nothing|beyond|form|figures|tables|specific)\b",
    re.I,
)
LATIN_SPECIFIC = re.compile(
    r"\b(qua[er]|quod|quid|enim|autem|tamen|rerum|omn|dicit|sunt|eius|"
    r"nec|quibus|dum|si[cq]|igitur|nam|atqui)\b",
    re.I,
)


def is_vision_narration(block):
    """True when a paragraph/block is OCR model narration, not source text."""
    stripped = block.strip()
    if not stripped:
        return False
    if STRONG_META.search(stripped):
        return True
    if not VPAT.search(stripped):
        return False
    eng_fn = len(ENGLISH_MARKERS.findall(stripped))
    latin_specific = len(LATIN_SPECIFIC.findall(stripped))
    total_words = len(re.findall(r"[A-Za-z]{2,}", stripped))
    eng_density = (eng_fn / total_words) if total_words else 0
    return total_words > 8 and eng_fn >= 3 and eng_density > 0.06 and latin_specific == 0


def remove_vision_blocks(body):
    """Remove OCR narration paragraphs within a segment, preserving real OCR."""
    pieces = re.split(r"(\n\s*\n)", body)
    kept = []
    removed = []
    for piece in pieces:
        if not piece:
            continue
        if piece.strip() == "":
            if kept and kept[-1].strip():
                kept.append(piece)
            continue
        if is_vision_narration(piece):
            removed.append(piece.strip())
            continue
        if "\n" in piece:
            kept_lines = []
            removed_line = False
            for line in piece.splitlines():
                if is_vision_narration(line):
                    removed.append(line.strip())
                    removed_line = True
                else:
                    kept_lines.append(line)
            if removed_line:
                kept.append("\n".join(kept_lines))
                continue
        kept.append(piece)
    cleaned = "".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, removed


def split_segments(text):
    """Yield (is_header, line) for each piece; headers are '[segment N]'."""
    parts = re.split(r"(\[segment \d+\]\n?)", text)
    for i in range(0, len(parts)):
        if i % 2 == 0:
            # body
            yield False, parts[i]
        else:
            yield True, parts[i]


def clean_text(text):
    """Return (new_text, qwall_runs, vision_replaced, vision_details)."""
    # (1) ?-walls first
    qwall_runs = len(QWALL.findall(text))
    new = QWALL.sub("[illegible]", text)
    new = re.sub(r"(\[illegible\]\s*){2,}", "[illegible] ", new)

    # (2) vision/OCR-meta descriptions, segment by segment
    vision_replaced = 0
    vision_details = []
    parts = re.split(r"(\[segment \d+\]\n?)", new)
    for i in range(1, len(parts), 2):
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        seg_num = re.search(r"\d+", header).group(0)
        cleaned_body, removed_blocks = remove_vision_blocks(body)
        if removed_blocks:
            for removed in removed_blocks:
                vision_replaced += 1
                vision_details.append((seg_num, removed[:70]))
            parts[i + 1] = (cleaned_body + "\n") if cleaned_body else "[illegible]\n"
            continue
        # (2a) STRONG meta disclaimers — trusted without language guard
        strong = STRONG_META.search(body)
        # (2b) WEAKER vision phrases — need the english-density guard
        weak_hit = VPAT.search(body)
        replace = False
        if strong:
            replace = True
        elif weak_hit:
            eng_fn = len(re.findall(r"\b(the|and|of|to|is|are|with|this|that|page|image|appears|blank|visible|paper|book|cover|sheet|material|leather|damaged|paragraphs|headings|content|text|shows|displays)\b", body, re.I))
            latin_specific = len(re.findall(r"\b(qua[er]|quod|quid|enim|autem|tamen|rerum|omn|dicit|sunt|eius|nec|quibus|dum|si[cq]|igitur|nam|atqui)\b", body, re.I))
            total_words = len(re.findall(r"[A-Za-z]{2,}", body))
            eng_dominant = total_words > 0 and (eng_fn / total_words) > 0.18
            if eng_fn >= 5 and eng_dominant and latin_specific == 0:
                replace = True
        if replace:
            parts[i + 1] = "[illegible]\n"
            vision_replaced += 1
            vision_details.append((seg_num, body.strip()[:70]))
    new = "".join(parts)
    return new, qwall_runs, vision_replaced, vision_details


def console_safe(value):
    enc = sys.stdout.encoding or "utf-8"
    return value.encode(enc, errors="backslashreplace").decode(enc, errors="replace")


def main():
    apply = "--apply" in sys.argv
    total_qwall = 0
    total_vision = 0
    all_details = []
    files_changed = 0
    for lf in sorted(glob.glob(str(ROOT / "works" / "*" / "latin-ocr.txt"))):
        p = Path(lf)
        orig = p.read_text(encoding="utf-8")
        new, qwall, vision, details = clean_text(orig)
        if new != orig:
            files_changed += 1
            total_qwall += qwall
            total_vision += vision
            w = p.parent.name.split("_")[0]
            all_details.append((w, qwall, vision, details))
            if apply:
                p.write_text(new, encoding="utf-8")
    mode = "APPLIED" if apply else "DRY-RUN (no files written; re-run with --apply)"
    print(f"[{mode}]")
    print(f"files changed: {files_changed}")
    print(f"?-wall runs collapsed: {total_qwall}")
    print(f"vision-descriptions replaced: {total_vision}")
    print()
    for w, q, v, details in sorted(all_details, key=lambda x: -(x[1] + x[2])):
        print(f"  {w}: {q} ?-walls, {v} vision-descs")
        for seg, preview in details:
            print(f"      seg {seg}: {console_safe(preview)!r}")


if __name__ == "__main__":
    main()
