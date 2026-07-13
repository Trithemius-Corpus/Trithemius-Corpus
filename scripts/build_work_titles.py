"""Derive clean display titles for every work from its researched intro.

The manifest titles are mangled PRDL shelfmarks ("Joh Tritthemii De
Scriptoribus Ecclesiasticis Liber", two indistinguishable "Polygraphiae
Libri Vi"). The intros open with the real title in the form

    *Latin Title* — "English gloss" — is Trithemius's ...

so we parse that. A handful of intros open differently (collected editions,
the Ecloga, the Clavis Polygraphiae); those are hand-mapped below.

Writes work_titles.json at the repo root: {id: {title, title_en}}.
The builders (manifest, site, work artifacts) read it and fall back to the
shelfmark only if an id is missing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKS = ROOT / "works"
OUT = ROOT / "work_titles.json"

# Intros that do not open with the standard *Title* — "gloss" — pattern.
OVERRIDES = {
    "prdl-24376_ecloga-de-laude-calvorum-ad-carolum": (
        "Ecloga de Laude Calvorum ad Carolum",
        "An Eclogue in Praise of Bald Men, to Charles",
    ),
    "prdl-24380_admonitiones-exhortationes-monachos": (
        "Admonitiones / Exhortationes ad Monachos",
        "Admonitions and Exhortations to Monks (later collected reprint)",
    ),
    "prdl-70281_clavis-generalis-triplex-in-libros-steganographicos": (
        "Clavis Generalis Triplex in Libros Steganographicos",
        "Threefold General Key to the Steganographic Books",
    ),
    "prdl-70282_clavis-polygraphiae-ioannis-trithemii-abbatis-diui": (
        "Clavis Polygraphiae",
        "Key to the Polygraphia",
    ),
    "prdl-70289_opera-historica-part": (
        "Opera Historica, Part I",
        "Collected Historical Works (Freher ed.), first part",
    ),
    "prdl-70290_opera-historica-part-chronicon-hirsaugiense-sponheimense": (
        "Opera Historica, Part II — Chronicon Hirsaugiense & Sponheimense",
        "Collected Historical Works, second part: the Hirsau and Sponheim chronicles",
    ),
}

# *Latin* — "English" —    (em dash or hyphen, curly or straight quotes)
PAT = re.compile(r'\*([^*]+)\*\s*[—-]\s*["“]([^"”]+)["”]')


def main() -> int:
    titles: dict[str, dict] = {}
    missing = []
    for d in sorted(WORKS.iterdir()):
        if not d.is_dir():
            continue
        intro = d / "intro.md"
        if not intro.exists():
            continue
        wid = d.name
        if wid in OVERRIDES:
            lat, en = OVERRIDES[wid]
        else:
            head = intro.read_text(encoding="utf-8").strip().split("\n", 1)[0]
            m = PAT.search(head)
            if not m:
                missing.append(wid)
                continue
            lat = m.group(1).strip()
            en = m.group(2).strip()
        titles[wid] = {"title": lat, "title_en": en}

    OUT.write_text(json.dumps(titles, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"wrote {OUT.name}: {len(titles)} titles")
    if missing:
        print(f"  [warn] could not parse {len(missing)}: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
