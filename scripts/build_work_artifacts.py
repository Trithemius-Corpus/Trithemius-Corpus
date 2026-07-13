"""Materialise the per-work artifacts the README promises, under works/<id>/.

For every translatable work this writes:
  - english.md      stitched English (shipping `public` backend, placeholders
                    excluded), with a small provenance header
  - latin-ocr.txt   the OCR-cleaned Latin exactly as the chunker fed it to the
                    translator (segments joined, blank-line separated)
  - metadata.json   the manifest slice for this work + artifact inventory
  - chunks/full_chunk_NNNN.md   the per-chunk English (the shipping backend)
  - chunks/grades.csv           per-chunk calibrated grades for this work

The site (parallel viewer) is the rendered view; these files are the dataset.
Run with the interpreter that has the harness chunker importable (Python313):

    python scripts/build_work_artifacts.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.json"
WORKS = ROOT / "works"

WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"
GRADES_CSV = CORPUS / "_quality" / "llm_grades_calibrated.csv"
PUBLIC_RELEASE_LEDGER = ROOT / "data" / "_quality" / "public_release_chunks.jsonl"
HARNESS_SCRIPTS = WORKING / "scripts"

CHUNK_MAX_CHARS = 4500
CHUNK_OCR_CLEANUP = True
PLACEHOLDER_RE = re.compile(r"<!--\s*skipped:", re.I)
GRADE_COLS = ["record", "translation_backend", "grader", "raw_faith",
              "adj_faith", "raw_fluent", "adj_fluent", "hallucinated",
              "preamble", "refusal", "notes"]
SOURCE_CANDIDATES = [
    "churro_full.txt",
    "full.txt",
    os.path.join("_churro_fold_backup", "full_qwen.txt"),
    "_full_preocr.txt",
]
SOURCE_PAGE_ILLEGIBLE_NOTE = (
    "[Source page illegible in the scan; the page image is the authoritative witness.]"
)
WRONG_SOURCE_SEGMENTS = {
    ("prdl-24368_de-operatione-divini-amoris", 2): SOURCE_PAGE_ILLEGIBLE_NOTE,
}

if str(HARNESS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(HARNESS_SCRIPTS))
from latin_translation_harness import records_from_file  # noqa: E402
from clean_latin_ocr import clean_text as clean_latin_ocr_text  # noqa: E402


_SCAN_JUNK = re.compile(
    r"""^\s*(?:
        -{2,}\s*Page\s*\d+\s*-{2,} | \#+\s*Translation |
        ©\s*(?:Herzog\ August|HAB|\[Autor|\[Author).* |
        Graph\..* |
        .*Persistent\s+URL.* |
        .*Persitent\s+URL.* |
        .*\[Signatur\].* |
        \[?\s*(?:BSB|Bayerische|StaatsBibliothek|M[üu]nchener|
            Digitalisierungs\w*|Digitale?\s+Biblioth\w+|Digital\s+Library|
            Herzog\ August\ Biblioth\w+|Dominus\ Augustus\ Bibliotheca|
            Terms\ of\ Use|Wolfenb[üu]ttel|
            dilibri|urn:nbn|VD\d{2}\s|Res/|Graph\.|Inc\.[a-z]|BSB-Ink|GW\ M\d|
            Creative\ Commons|Trithemius,\ Johannes)\b.*
    )\s*$""",
    re.I | re.X,
)

_EN_SCAN_JUNK = re.compile(
    r"""^\s*(?:
        BSB.*(?:Bayerische|Bavarian|Staatsbibliothek|Digitization|Digitalisierungszentrum).* |
        Herzog\ August\ (?:Bibliothek|Library).* |
        Dominus\ Augustus\ Bibliotheca.* |
        ©\s*(?:Herzog\ August|HAB|\[Author|\[author).* |
        .*Persistent\s+URL.* |
        .*\[Call\ number\].* |
        .*\[Shelfmark\].* |
        Bavarian\ State\ Library.* |
        Bayerische\ Staatsbibliothek.* |
        M[Ã¼üu]nchener\ Digitalisierungs\w+.* |
        Munich\ Digitization\ Cent(?:er|re).* |
        Digitale?\s+Biblioth\w+.* |
        Digital\ Library.* |
        Trithemius,\ Johannes.* |
        urn:nbn:.* |
        VD16\b.* |
        BSB-Ink\b.* |
        GW\s+M\d+.* |
        Res/.* |
        Graph\.(?:\s*\d+.*)? |
        College\ of\ the\ Society.* |
        \[?(?:Library|The\ remaining\ pages\ are\ blank).*Bavarian\ State\ Library.*\]?
    )\s*$""",
    re.I | re.X,
)

_HAB_NOTICE_HEAD = re.compile(
    r"(Herzog\ August|HAB|Wolfenb|Persistent\s+URL|diglib\.hab)",
    re.I,
)
_HAB_NOTICE_END = re.compile(r"(?:Der|The)\s+Dire(?:ktor|ctor)\s+\(2013-03-01\)", re.I)
_HAB_TRAILING_JUNK = re.compile(
    r"""^\s*(?:
        ```(?:plaintext)? |
        Herzog\ August\ (?:Bibliothek|Library) |
        Wolfenb.* |
        Wolffenb.* |
        Wolfsb.* |
        Yg|51|HELMST|8[Â°°]?
    )\s*$""",
    re.I | re.X,
)


def strip_leading_hab_notice(text: str) -> str:
    """Remove HAB usage/citation boilerplate that was OCRed as content."""
    lines = text.splitlines()
    if not _HAB_NOTICE_HEAD.search("\n".join(lines[:80])):
        return text

    end = None
    for idx, line in enumerate(lines[:120]):
        if _HAB_NOTICE_END.search(line):
            end = idx + 1
            break
    if end is None:
        return text

    while end < len(lines):
        line = lines[end].strip()
        if not line or _HAB_TRAILING_JUNK.match(line):
            end += 1
            continue
        break
    return "\n".join(lines[end:])


def strip_scan_boilerplate(text: str) -> str:
    text = strip_leading_hab_notice(text)
    kept = [
        ln for ln in text.splitlines()
        if not _SCAN_JUNK.match(ln) and not _HAB_TRAILING_JUNK.match(ln)
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def strip_english_scan_boilerplate(text: str) -> str:
    text = strip_leading_hab_notice(text)
    kept = [ln for ln in text.splitlines() if not _EN_SCAN_JUNK.match(ln)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def clean_chunk(raw: str) -> str:
    t = raw.strip()
    t = re.sub(r"^#+\s*Translation\s*", "", t)
    t = re.sub(r"^\*{0,2}-{0,3}\s*Page\s*\d+\s*-{0,3}\*{0,2}\s*$", "", t, flags=re.M | re.I)
    t = re.sub(r"^\s*-{2,}\s*Page\s*\d+\s*-{2,}\s*$", "", t, flags=re.M | re.I)
    return strip_english_scan_boilerplate(t)


# Sentence-ending punctuation that should cause a paragraph break at a chunk seam.
# Matches a run of closing quotes/brackets after a . ! or ? (e.g. ...amen." or ...end.])
_SENT_END_RE = re.compile(r'[.!?]["\'\u201d\u2019\)\]]*\s*$')


def stitch_english(blocks: list[str]) -> str:
    """Join per-chunk English blocks with a smart seam.

    The old behaviour joined every chunk with a blank line, which split
    sentences in half when the chunk boundary fell mid-sentence (the
    corpus's most visible systemic defect — ~135 of 267 seams in one
    work). Now a seam becomes a paragraph break only when the preceding
    chunk ends a sentence; otherwise the blocks are joined with a single
    space (a continuation of the same sentence). A trailing hyphen at the
    seam is treated as a soft hyphen and the space dropped, so
    hyphenated line-breaks ("cla- / rius") rejoin into one word.
    """
    out: list[str] = []
    for body in blocks:
        if not body:
            continue
        if not out:
            out.append(body)
            continue
        prev = out[-1].rstrip()
        cur = body.lstrip()
        if prev.endswith("-"):
            # soft hyphen / line-break hyphen: rejoin into one word
            out[-1] = prev[:-1] + cur
        elif _SENT_END_RE.search(prev + "\n") or _SENT_END_RE.search(prev):
            # previous chunk ended a sentence -> new paragraph
            out[-1] = prev
            out.append(cur)
        else:
            # mid-sentence seam -> join with a space (no paragraph break)
            out[-1] = prev + " " + cur
    return "\n\n".join(out)



def load_manifest_works() -> list[dict]:
    return [w for w in json.loads(MANIFEST.read_text(encoding="utf-8"))["works"]
            if not w.get("skip")]


def choose_source_records(work_dir: Path, pub_dir: Path) -> tuple[Path, list[dict], list[tuple[Path, list[dict]]]]:
    """Pick the OCR stream that matches the public translation chunk stream."""
    target = len(list(pub_dir.glob("full_chunk_*.md")))
    candidates: list[tuple[int, int, Path, list[dict]]] = []
    for priority, rel in enumerate(SOURCE_CANDIDATES):
        path = work_dir / rel
        if not path.exists():
            continue
        recs = records_from_file(path, None, CHUNK_MAX_CHARS, 0, CHUNK_OCR_CLEANUP)
        candidates.append((abs(len(recs) - target), priority, path, recs))
    if not candidates:
        return work_dir / "full.txt", [], []
    candidates = sorted(candidates, key=lambda item: (item[0], item[1]))
    _, _, path, recs = candidates[0]
    return path, recs, [(candidate_path, candidate_recs)
                        for _, _, candidate_path, candidate_recs in candidates]


def source_body_for(
    wid: str,
    seg_num: int,
    primary_text: str,
    candidates: list[tuple[Path, list[dict]]],
) -> tuple[str, Path | None]:
    """Return cleaned Latin, filling blank primary segments from peer streams."""
    body = strip_scan_boilerplate(primary_text)
    if not body.strip():
        for path, recs in candidates:
            if seg_num > len(recs):
                continue
            alt = strip_scan_boilerplate(recs[seg_num - 1]["text"])
            if alt.strip():
                body = alt
                return WRONG_SOURCE_SEGMENTS.get((wid, seg_num), body), path
    return WRONG_SOURCE_SEGMENTS.get((wid, seg_num), body), None


def grades_for(work_id: str) -> list[dict]:
    rows: list[dict] = []
    out = []
    if GRADES_CSV.exists():
        with GRADES_CSV.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("work_id") == work_id:
                    if row.get("translation_backend") == "public":
                        row = dict(row)
                        row["translation_backend"] = "public-history"
                    out.append(row)
    rows.extend(out)
    if PUBLIC_RELEASE_LEDGER.exists():
        with PUBLIC_RELEASE_LEDGER.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("work_id") != work_id:
                    continue
                rows.append({
                    "record": row.get("record", ""),
                    "translation_backend": row.get("translation_backend", "public"),
                    "grader": row.get("grader", ""),
                    "raw_faith": row.get("raw_faith", ""),
                    "adj_faith": row.get("adj_faith", ""),
                    "raw_fluent": row.get("raw_fluent", ""),
                    "adj_fluent": row.get("adj_fluent", ""),
                    "hallucinated": row.get("hallucinated", False),
                    "preamble": row.get("preamble", False),
                    "refusal": row.get("refusal", False),
                    "notes": row.get("notes", ""),
                })
    return rows


def build_one(w: dict) -> dict:
    wid = w["id"]
    corpus_dir = CORPUS / wid
    pub = CORPUS / wid / "translations" / "public" / "full"
    wdir = WORKS / wid
    wdir.mkdir(parents=True, exist_ok=True)

    if not pub.is_dir():
        return {"id": wid, "skipped": "no source/translation"}

    source_path, recs, source_candidates = choose_source_records(corpus_dir, pub)
    if not recs:
        return {"id": wid, "skipped": "no source/translation"}

    # latin-ocr.txt
    fallback_sources: dict[str, int] = {}
    latin_blocks = []
    for i, r in enumerate(recs, 1):
        body, fallback_path = source_body_for(wid, i, r["text"], source_candidates)
        if fallback_path is not None and fallback_path != source_path:
            fallback_sources[str(fallback_path.relative_to(corpus_dir))] = (
                fallback_sources.get(str(fallback_path.relative_to(corpus_dir)), 0) + 1
            )
        latin_blocks.append(f"[segment {i}]\n{body}")
    latin = "\n\n".join(latin_blocks)
    latin, _, _, _ = clean_latin_ocr_text(latin)
    (wdir / "latin-ocr.txt").write_text(latin + "\n", encoding="utf-8")

    # chunks/ + stitched english
    chunks_dir = wdir / "chunks"
    if chunks_dir.exists():
        shutil.rmtree(chunks_dir)
    chunks_dir.mkdir()
    eng_blocks, n_missing = [], 0
    # Stitch every published chunk, not just the first len(recs): the public
    # lane can legitimately outrun the Latin record count (tail matter split
    # differently at translation time), and capping at len(recs) silently
    # drops real content (prdl-70280 lost its closing letter this way).
    pub_nums = [
        int(m.group(1))
        for f in pub.glob("full_chunk_*.md")
        if (m := re.match(r"full_chunk_(\d+)\.md$", f.name))
    ]
    n_total = max(len(recs), max(pub_nums, default=0))
    for i in range(1, n_total + 1):
        ef = pub / f"full_chunk_{i:04d}.md"
        if not ef.exists():
            n_missing += 1
            continue
        raw = ef.read_text(encoding="utf-8", errors="replace")
        artifact_body = clean_chunk(raw)
        (chunks_dir / f"full_chunk_{i:04d}.md").write_text(
            (artifact_body if artifact_body else "<!-- removed: source digitization boilerplate -->") + "\n",
            encoding="utf-8",
        )
        if PLACEHOLDER_RE.search(raw[:200]):
            n_missing += 1
            continue
        body = artifact_body
        if body:
            eng_blocks.append(body)
        else:
            n_missing += 1

    title = w.get("title", wid)
    header = (
        f"# {title}\n\n"
        f"> Machine-assisted English translation. Work `{wid}`. "
        f"Tier {w.get('tier','?')} · faithful {w.get('faithful_adj','?')} "
        f"(GPT-5.5 audit). See `../../METHODOLOGY.md` (Limitations). Backend: "
        f"`{w.get('canonical_backend','public')}`.\n\n---\n\n"
    )
    (wdir / "english.md").write_text(
        header + stitch_english(eng_blocks) + "\n", encoding="utf-8")

    # metadata.json
    grows = grades_for(wid)
    meta = {
        "id": wid,
        "title": title,
        "year": w.get("year"),
        "source_year": w.get("source_year"),
        "year_note": w.get("year_note"),
        "edition_info": w.get("edition_info"),
        "edition_info_raw": w.get("edition_info_raw"),
        "duplicate_source_group": w.get("duplicate_source_group"),
        "duplicate_source_note": w.get("duplicate_source_note"),
        "page_count": w.get("page_count"),
        "genre_cluster": w.get("genre_cluster"),
        "tier": w.get("tier"),
        "faithful_adj": w.get("faithful_adj"),
        "fluent_adj": w.get("fluent_adj"),
        "coverage_pct": w.get("coverage_pct"),
        "chunks_graded": w.get("chunks_graded"),
        "chunks_total": w.get("chunks_total"),
        "hallucinated_pct": w.get("hallucinated_pct"),
        "low_pct": w.get("low_pct"),
        "canonical_backend": w.get("canonical_backend"),
        "all_backends": w.get("all_backends"),
        "source": w.get("source"),
        "license": "CC0-1.0",
        "artifacts": {
            "english_md": "english.md",
            "latin_ocr_txt": "latin-ocr.txt",
            "intro_md": "intro.md" if (wdir / "intro.md").exists() else None,
            "chunks_dir": "chunks/",
            "n_segments": len(recs),
            "n_missing_segments": n_missing,
            "latin_source_file": str(source_path.relative_to(corpus_dir)),
            "latin_fallback_sources": fallback_sources,
            "parallel_viewer": f"https://trithemius-corpus.github.io/Trithemius-Corpus/works/{wid}_parallel.html",
        },
    }
    (wdir / "metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # chunks/grades.csv (per-chunk calibrated grades for this work)
    if grows:
        with (chunks_dir / "grades.csv").open("w", encoding="utf-8", newline="") as fh:
            wri = csv.DictWriter(fh, fieldnames=GRADE_COLS, extrasaction="ignore")
            wri.writeheader()
            for r in grows:
                wri.writerow(r)

    return {"id": wid, "segments": len(recs), "missing": n_missing,
            "english_blocks": len(eng_blocks)}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=None,
                    help="rebuild only works whose id starts with this (repeatable)")
    ns = ap.parse_args()
    works = load_manifest_works()
    if ns.only:
        works = [w for w in works if any(w["id"].startswith(p) for p in ns.only)]
        print(f"restricted to {len(works)} work(s): {[w['id'][:20] for w in works]}")
    results = [build_one(w) for w in works]
    ok = [r for r in results if "skipped" not in r]
    skipped = [r for r in results if "skipped" in r]
    print(f"wrote artifacts for {len(ok)}/{len(works)} works")
    tot_missing = sum(r.get("missing", 0) for r in ok)
    print(f"  total segments missing a translation: {tot_missing}")
    for r in skipped:
        print(f"  SKIPPED {r['id']}: {r['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
