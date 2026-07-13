#!/usr/bin/env python3
"""Build site/static/cipher-data.json from the working-corpus Style C tables.

Parses Trithemius's verbal-substitution ("Ave Maria") tables and the
Steganographia "Table of Direction" into a single JSON the cipher-lab page
consumes. Pure parsing of already-rendered markdown tables — no invention.

Run directly (``python scripts/build_cipher_data.py``) or as a build step.
The output is auto-shipped to site/dist/static/ by build_site.copy_static().
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "site" / "static"

# Working corpus lives outside the repo. Two known roots to try.
WORK_ROOTS = [
    Path(r"E:\trithemius\data\corpus"),
    Path(r"E:/trithemius/data/corpus"),
]

ALPHABET_24 = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "k", "l", "m",
               "n", "o", "p", "q", "r", "s", "t", "v", "x", "y", "z", "w"]


def _find_work_dir(work_id: str) -> Path | None:
    for root in WORK_ROOTS:
        p = root / work_id
        if p.exists():
            return p
    return None


def _parse_markdown_table(text: str) -> tuple[list[str], list[list[str]]] | None:
    """Return (headers, rows) from the first markdown pipe table in `text`,
    or None if there is none."""
    lines = text.splitlines()
    rows = []
    headers = None
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        # separator row?
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        if headers is None:
            headers = cells
            continue
        rows.append(cells)
    if headers is None:
        return None
    return headers, rows


def parse_ave_maria(work_id: str) -> dict:
    """Parse all substitution-table chunks into a {alphabet, columns} set.

    Each chunk is one multi-column alphabetum: rows keyed by the 24-letter
    alphabet, columns = substitution alphabets (col A..). We aggregate every
    column across all chunks into a flat list of named columns so the encoder
    can rotate through them by position. Columns with too many empty cells
    (OCR loss) are skipped."""
    work = _find_work_dir(work_id)
    out = {"alphabet": ALPHABET_24, "columns": [], "chunk_count": 0}
    if work is None:
        return out
    key_dir = work / "translations" / "style-c-cipher-key" / "full"
    if not key_dir.exists():
        return out
    chunks = sorted(key_dir.glob("full_chunk_*.md"))
    out["chunk_count"] = len(chunks)
    for chunk in chunks:
        parsed = _parse_markdown_table(chunk.read_text(encoding="utf-8"))
        if not parsed:
            continue
        headers, rows = parsed
        # build a {letter: cell} per row, keyed by first column
        by_letter: dict[str, list[str]] = {}
        for row in rows:
            if not row:
                continue
            letter = row[0].strip().strip("`").lower()
            by_letter[letter] = row[1:]
        # emit each named column as its own substitution alphabet
        for ci, col_header in enumerate(headers[1:]):
            mapping: dict[str, str] = {}
            empty = 0
            for letter in ALPHABET_24:
                cells = by_letter.get(letter, [])
                val = cells[ci].strip() if ci < len(cells) else ""
                if val:
                    mapping[letter] = val
                else:
                    empty += 1
            # keep columns that are at least half-populated (drop OCR-lost ones)
            if len(mapping) >= len(ALPHABET_24) // 2:
                out["columns"].append({
                    "name": f"{chunk.stem} · {col_header}",
                    "chunk": chunk.stem,
                    "words": mapping,
                })
    return out


def parse_spirits(work_id: str) -> list[dict]:
    """Parse the Steganographia 'Table of Direction' (16 cardinal princes).

    The table is a fixed run of lines like ``East. Pamerfiel. T 1000. 10000. 10. 0.0.``
    Each line = wind-direction + planetary prince + astrological glyph(s) +
    four numeric offices (day-dukes / night-dukes / servants / etc.)."""
    eng = ROOT / "works" / work_id / "english.md"
    spirits: list[dict] = []
    if not eng.exists():
        return spirits
    text = eng.read_text(encoding="utf-8")
    # Find the table run: it opens with the East/Pamersiel line and runs until
    # a blank line. Each line: "<Direction>. <Prince>[.] <glyphs> <numbers>"
    # The prince's trailing period is optional (some OCR lines omit it).
    table_re = re.compile(
        r"^([A-Z][a-z]+)\.\s+([A-Z][a-z]+(?:iel|iel|as|el|oth|ael|garas|ymiel))\.?\s+(.+)$",
        re.M,
    )
    # collect the contiguous run of matching lines (Table of Direction = ~16
    # consecutive lines, one per compass wind). Group matches whose start is
    # within 80 chars of the previous match's end.
    matches = list(table_re.finditer(text))
    groups: list[list[re.Match]] = []
    for m in matches:
        if groups and m.start() - groups[-1][-1].end() <= 80:
            groups[-1].append(m)
        else:
            groups.append([m])
    table = max(groups, key=len) if groups else []
    # locate each prince's first mention in the chunk files, for cross-linking
    chunks_dir = ROOT / "works" / work_id / "chunks"
    seg_cache: dict[str, int] = {}
    def first_segment(name: str) -> int | None:
        if name in seg_cache:
            return seg_cache[name]
        if not chunks_dir.exists():
            return None
        for cf in sorted(chunks_dir.glob("full_chunk_*.md")):
            if name in cf.read_text(encoding="utf-8"):
                m = re.search(r"(\d+)", cf.stem)
                seg_cache[name] = int(m.group(1)) if m else None
                return seg_cache[name]
        seg_cache[name] = None
        return None

    for m in table:
        direction, prince, rest = m.group(1), m.group(2), m.group(3)
        # rest = glyphs + dot-separated numbers; split numbers off the end
        nums = re.findall(r"\d[\d.]*", rest)
        glyphs = re.sub(r"\d[\d.]*", "", rest).strip().rstrip(".")
        spirits.append({
            "name": prince,
            "direction": direction,
            "glyphs": glyphs,
            "numbers": nums,
            "segment": first_segment(prince),
            "work_id": work_id,
        })
    return spirits


def parse_numerical_letters(work_id: str) -> dict:
    """Parse the 'Order of numerical letters' tables into a number→code mapping.

    The primary table is a run of ``code value code value ...`` lines (several
    pairs per line) under the first 'Order of numerical letters' heading. We
    only accept codes that look like Trithemius's positional letter-codes:
    lowercase Latin letters, optionally with a trailing ``w`` or a digit pair
    (e.g. ``a``, ``ma``, ``nja``, ``cw``, ``2w``, ``p ij``). The OCR source has
    collisions (``cw``→3000 and 5000) — surfaced as ambiguous."""
    eng = ROOT / "works" / work_id / "english.md"
    out = {"by_number": {}, "ambiguous": [], "note": ""}
    if not eng.exists():
        return out
    text = eng.read_text(encoding="utf-8")
    # only the FIRST "Order of numerical letters" run, up to the next blank
    # paragraph break. Heading is italic in the source: *Order...letters.*
    m = re.search(r"numerical letters\.\*\n\n([\s\S]*?)\n\n", text)
    block = m.group(1) if m else ""
    # a code: lowercase letters a-z, optionally a second letter (ma, ka, nj),
    # optionally a 'j' (nj, nja), optionally trailing 'w' (bw, cw, 2w, kw)
    code_re = re.compile(r"^(?:[a-z]{1,3}j?[a-z]?|[a-z][a-z]?w|[2-9]w|w\d?)$")
    pairs: dict[int, list[str]] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        toks = line.split()
        i = 0
        while i + 1 < len(toks):
            code, val = toks[i], toks[i + 1]
            num = re.match(r"^(\d{1,9})$", val)
            if num and code_re.match(code):
                n = int(num.group(1))
                pairs.setdefault(n, [])
                if code not in pairs[n]:
                    pairs[n].append(code)
                i += 2
            else:
                i += 1
    by_number = {}
    ambiguous = []
    for n, codes in sorted(pairs.items()):
        if len(codes) == 1:
            by_number[n] = codes[0]
        else:
            ambiguous.append({"number": n, "codes": codes})
            by_number[n] = codes[0]
    # also flag codes that map to MORE than one number (the real ambiguity in
    # this OCR source: e.g. 'cw' → 3000 and 5000). These are code→number
    # collisions, surfaced so the calculator can warn when it returns one.
    by_code: dict[str, list[int]] = {}
    for n, code in by_number.items():
        by_code.setdefault(code, []).append(n)
    ambiguous_codes = {c: ns for c, ns in by_code.items() if len(ns) > 1}
    out["by_number"] = by_number
    out["ambiguous"] = ambiguous
    out["ambiguous_codes"] = ambiguous_codes
    out["note"] = ("Trithemius's positional letter-codes. Some codes collide in "
                   "the OCR'd source; codes mapping to multiple numbers are "
                   "flagged in 'ambiguous_codes'.")
    return out


def build() -> dict:
    poly = "prdl-24390_polygraphiae-libri-vi"
    steg = "prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam"
    data = {
        "source": "Parsed from the Trithemius Corpus Style C tables "
                  "(Polygraphia VI cipher-key chunks; Steganographia Table of Direction).",
        "alphabet_24": ALPHABET_24,
        "ave_maria": parse_ave_maria(poly),
        "tabula_recta": {
            "alphabet": ALPHABET_24,
            "note": "Caesar-rotation over the 24-letter Latin alphabet "
                    "(no j; v/u and w at the end). Generated algorithmically — "
                    "the OCR'd grid is partially corrupt.",
        },
        "numerical_letters": parse_numerical_letters(poly),
        "spirits": parse_spirits(steg),
    }
    return data


def main() -> None:
    data = build()
    out_path = STATIC / "cipher-data.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    n_cols = len(data["ave_maria"]["columns"])
    n_spirits = len(data["spirits"])
    print(f"wrote {out_path} "
          f"({n_cols} substitution columns, {n_spirits} spirits)")


if __name__ == "__main__":
    main()
