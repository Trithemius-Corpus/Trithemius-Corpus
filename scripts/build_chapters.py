"""Recover chapter/book structure for each work and write chapters.json.

For each work:
  1. Scan latin-ocr.txt for structural headings (LIBER, CAPUT, PRAEFATIO,
     PROOEMIUM, Tractatus, Modus, Argumentum) with a fuzzy/OCR-tolerant regex.
  2. Map each heading's char offset to a segment number via records_from_file
     cumulative chunk lengths (same chunker the build uses).
  3. Clean the heading label (normalize OCR scannos, title-case).
  4. Build hierarchy (group CAPUT under preceding LIBER) and collapse dense
     Modi into ranges.
  5. If <3 real headings recovered, fall back to even length-sections
     ("Part 1 of N").

Output: works/<id>/chapters.json
  {"source": "headings"|"length", "entries": [{"label": "...", "n": <seg>, "title": "..."}]}

Idempotent. Run from E:\\trithemius-corpus BEFORE build_site.py.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKS = ROOT / "works"
LATROOT = Path(r"E:\trithemius\data\corpus")
sys.path.insert(0, str(Path(r"E:\trithemius\scripts")))
from latin_translation_harness import records_from_file

ROMAN = r"(?:[IVXLCDM]{1,8}|primus|secundus|tertius|quartus|quintus|sextus|septimus|octavus|nonus|decimus|undecimus|duodecimus)"
# heading markers, tolerant of OCR damage (lowercase e in CAPUT/LIBER, æ ligatures, etc.)
HEADING_RE = re.compile(
    r"(?im)^\s*(?:"
    # LIBER with roman: "LIBER I", "liber secundus", "Lib. II" (roman must be whole word)
    r"(?P<liber>L[Ii][BbEe][FfEe][Rr])\.?\s+(?P<lrom>" + ROMAN + r")\b"
    # standalone LIBER on its own line (Fraktur b/f confusion)
    r"|(?P<liber_solo>L[Ii][BbEe][FfEe][Rr])\s*$"
    # CAPUT with roman
    r"|(?P<caput>C[AaÄä]?[Pp][Uu][Tt])\.?\s+(?P<crom>" + ROMAN + r")\b"
    # standalone CAPUT
    r"|(?P<caput_solo>C[AaÄä]?[Pp][Uu][Tt])\s*$"
    # PRAEFATIO / PROOEMIUM
    r"|(?P<praef>P[Rr][AäA][EeÄä]?[Ff][Aa][Tt][Ii][Oo][Nn]?)"
    r"|(?P<prooem>[Pp][Rr][Oo][OoÄä]?[EeÄä]?[Mm][Ii][Uu][Mm])"
    # TRACTATUS (with or without roman)
    r"|(?P<tract>[Tt][Rr][Aa][Cc][Tt][Aa][Tt][Uu][Ss])\.?(?:\s+(?P<trom>" + ROMAN + r")\b)?"
    # MODUS with roman
    r"|(?P<modus>[Mm][Oo][Dd][Uu][Ss])\.?\s+(?P<mrom>" + ROMAN + r")\b"
    # ANNOTATIO (recurring section header in catalogues)
    r"|(?P<annot>A[Nn][Nn][Oo][Tt][Aa][Tt][Ii][Oo]\s*[A-Za-z]*)"
    r"|(?P<arg>[AaÄä][Rr][Gg][Uu][Mm][EeÄä][Nn][Tt][Uu][Mm])"
    r")\s*(?P<rest>[^\n]{0,80})\s*$"
)
# For book/chapter counters: a standalone LIBER increments the book count
BOOK_ONLY_RE = re.compile(r"(?im)^\s*L[Ii][BbEe][FfEe][Rr]\s*$")
CAPUT_ONLY_RE = re.compile(r"(?im)^\s*C[AaÄä]?[Pp][Uu][Tt]\s*$")


def roman_to_int(s):
    s = s.lower().strip(".")
    word_map = {"primus":1,"secundus":2,"tertius":3,"quartus":4,"quintus":5,
                "sextus":6,"septimus":7,"octavus":8,"nonus":9,"decimus":10,
                "undecimus":11,"duodecimus":12}
    if s in word_map:
        return word_map[s]
    roman = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}
    s = s.upper()
    total, prev = 0, 0
    for c in reversed(s):
        v = roman.get(c, 0)
        total = total - v if v < prev else total + v
        prev = v
    return total or 0


def clean_rest(rest):
    """Clean the trailing title text after a heading marker."""
    rest = rest.strip(" .:,—-")
    # drop OCR ligature artifacts
    rest = rest.replace("æ", "ae").replace("Æ", "AE").replace("œ", "oe")
    rest = re.sub(r"\s+", " ", rest)
    if len(rest) < 3:
        return ""
    # title-case, cap length
    rest = rest[:70]
    return rest


def offset_to_seg(offset, offsets):
    """Map a char offset to a 1-based segment number given cumulative chunk offsets."""
    for i in range(len(offsets) - 1):
        if offsets[i] <= offset < offsets[i + 1]:
            return i + 1
    return len(offsets)  # last


def build_from_headings(lat_text, offsets, n_segs):
    """Recover structured headings -> list of entries."""
    raw = []
    for m in HEADING_RE.finditer(lat_text):
        offset = m.start()
        seg = offset_to_seg(offset, offsets)
        rest = clean_rest(m.group("rest") or "")
        if m.group("liber") or m.group("liber_solo"):
            num = roman_to_int(m.group("lrom")) if m.group("lrom") else 0
            raw.append(("liber", num, seg, rest))
        elif m.group("caput") or m.group("caput_solo"):
            num = roman_to_int(m.group("crom")) if m.group("crom") else 0
            raw.append(("caput", num, seg, rest))
        elif m.group("praef"):
            raw.append(("pref", 0, seg, "Preface"))
        elif m.group("prooem"):
            raw.append(("pref", 0, seg, "Prooemium"))
        elif m.group("tract"):
            num = roman_to_int(m.group("trom")) if m.group("trom") else 0
            raw.append(("tract", num, seg, rest))
        elif m.group("modus"):
            raw.append(("modus", roman_to_int(m.group("mrom")), seg, rest))
        elif m.group("annot"):
            raw.append(("annot", 0, seg, "Annotationes"))
        elif m.group("arg"):
            raw.append(("pref", 0, seg, "Argument"))

    if len(raw) < 3:
        return None

    # de-duplicate headings landing on the same segment (keep first)
    seen_seg = set()
    dedup = []
    for kind, num, seg, title in raw:
        if seg in seen_seg:
            continue
        seen_seg.add(seg)
        dedup.append((kind, num, seg, title))

    # assign sequential numbers to standalone (num==0) markers
    liber_counter = 0
    caput_counter = 0
    tract_counter = 0
    fixed = []
    for kind, num, seg, title in dedup:
        if kind == "liber":
            liber_counter = num if num else liber_counter + 1
            if not num:
                num = liber_counter
            caput_counter = 0
        elif kind == "caput":
            caput_counter = num if num else caput_counter + 1
            if not num:
                num = caput_counter
        elif kind == "tract":
            tract_counter = num if num else tract_counter + 1
            if not num:
                num = tract_counter
        fixed.append((kind, num, seg, title))
    dedup = fixed

    # build labels with hierarchy
    current_book = 0
    current_caput_in_book = 0
    entries = []
    # collapse dense modi
    modi_segs = [(num, seg) for kind, num, seg, t in dedup if kind == "modus"]
    modi_seg_set = {seg for _, seg in modi_segs}
    modi_ranges = {}
    if len(modi_segs) >= 8:
        nums = sorted(n for n, _ in modi_segs)
        runs = []
        run = [nums[0]]
        for n in nums[1:]:
            if n == run[-1] + 1:
                run.append(n)
            else:
                runs.append(run); run = [n]
        runs.append(run)
        for r in runs:
            lo_seg = next(s for num, s in modi_segs if num == r[0])
            if len(r) == 1:
                modi_ranges[lo_seg] = f"Modus {to_roman(r[0])}"
            else:
                modi_ranges[lo_seg] = f"Modi {to_roman(r[0])}\u2013{to_roman(r[-1])}"

    for kind, num, seg, title in dedup:
        if seg in modi_ranges and kind == "modus":
            if not any(e["n"] == seg for e in entries):
                entries.append({"label": modi_ranges[seg], "n": seg, "title": ""})
            continue
        if kind == "modus" and seg in modi_seg_set and len(modi_segs) >= 8:
            continue
        if kind == "liber":
            current_book = num
            current_caput_in_book = 0
            label = f"Book {to_roman(num)}" + (f" \u2014 {title}" if title else "")
        elif kind == "caput":
            current_caput_in_book += 1
            if current_book:
                label = f"Book {to_roman(current_book)} / Ch {current_caput_in_book}" + (f": {title}" if title else "")
            else:
                label = f"Chapter {num}" + (f": {title}" if title else "")
        elif kind == "tract":
            label = f"Tractate {to_roman(num)}" + (f" \u2014 {title}" if title else "")
        elif kind == "modus":
            label = f"Modus {to_roman(num)}" + (f" \u2014 {title}" if title else "")
        elif kind == "annot":
            label = "Annotationes Scriptorum"
        else:  # pref / arg
            label = title or "Preface"
        entries.append({"label": label, "n": seg, "title": title})

    # dedupe consecutive same-label, sort by segment
    entries.sort(key=lambda e: e["n"])
    out = []
    last_label = None
    for e in entries:
        if e["label"] == last_label:
            continue
        out.append(e)
        last_label = e["label"]
    return out if len(out) >= 3 else None


ROMAN_NUMS = [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),
              (50,"L"),(40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]
def to_roman(n):
    if not n or n < 1: return str(n)
    out = ""
    for v, s in ROMAN_NUMS:
        while n >= v:
            out += s; n -= v
    return out


def build_from_length(n_segs):
    """Even-split fallback: Part 1 of N."""
    if n_segs <= 1:
        return None
    n_parts = max(2, min(12, (n_segs + 4) // 5))
    step = n_segs / n_parts
    entries = []
    for i in range(n_parts):
        seg = int(round(i * step)) + 1
        seg = min(seg, n_segs)
        if not entries or entries[-1]["n"] != seg:
            entries.append({"label": f"Part {i+1} of {n_parts}", "n": seg, "title": ""})
    return entries


def main():
    written = 0
    head_works = 0
    length_works = 0
    for wd in sorted(WORKS.iterdir()):
        if not wd.is_dir():
            continue
        lat_path = wd / "latin-ocr.txt"
        if not lat_path.exists():
            continue
        lat_text = lat_path.read_text(encoding="utf-8", errors="replace")
        # chunk via the same chunker the build uses
        work_lat = LATROOT / wd.name / "full.txt"
        try:
            recs = records_from_file(work_lat, None, 4500, 0, True) if work_lat.exists() else \
                   records_from_file(lat_path, None, 4500, 0, True)
        except Exception:
            continue
        n_segs = len(recs)
        offsets = [0]
        for r in recs:
            offsets.append(offsets[-1] + len(r["text"]))

        entries = build_from_headings(lat_text, offsets, n_segs)
        source = "headings"
        if not entries:
            entries = build_from_length(n_segs)
            source = "length"
        if not entries:
            continue
        out = {"source": source, "n_segments": n_segs, "entries": entries}
        (wd / "chapters.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        written += 1
        if source == "headings":
            head_works += 1
        else:
            length_works += 1
    print(f"wrote {written} chapters.json  (headings: {head_works}, length: {length_works})")


if __name__ == "__main__":
    main()
