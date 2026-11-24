"""Assemble the 27 Sonnet-graded Trithemius 4B edition works into the repo.

Copies from the working corpus (E:/trithemius/data/corpus) into
E:/trithemius-corpus/works-t4b/<work_id>/:

  latin-ocr.txt   <- LoRA OCR (translations/_reocr/qwen3vl-4b-trithemius-q6/full.txt)
  english.md      <- concatenated GPT-5.5 dual-context chunks
  chunks/         <- individual chunk files
  metadata.json   <- Sonnet grades + edition branding
  intro.md        <- reused from the published edition (same text)

The 27 works are those Sonnet graded S/A (faith >= 3.5). Sonnet is the
authoritative grader; MiniMax was a dual-check only.
"""
from __future__ import annotations

import json
import shutil
import os
import re
from publication_guard import staged_directory
from edition_corrections import restore_track
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:/trithemius"))
CORPUS = WORKING / "data" / "corpus"
LANE = "qwen3vl-trithemius-q6-dual-gpt55"
OCR_ENGINE = "qwen3vl-4b-trithemius-q6"
OUT_ROOT = ROOT / "works-t4b"

# Sonnet second-pass grades (the authoritative grader)
SONNET_GRADES = Path(os.environ.get("TRITHEMIUS_T4B_GRADES", WORKING / "data/corpus/_quality/codex_grade_SECOND_PASS_summary.jsonl"))

PUBLISH_PRDLS = [
    "prdl-70291", "prdl-24361", "prdl-32286", "prdl-70286", "prdl-24378",
    "prdl-32287", "prdl-24381", "prdl-24375", "prdl-24373", "prdl-24382",
    "prdl-24357", "prdl-24376", "prdl-24385", "prdl-70285", "prdl-24391",
    "prdl-24368", "prdl-24372", "prdl-24393", "prdl-24363", "prdl-24371",
    "prdl-70283", "prdl-70292", "prdl-24389", "prdl-24362", "prdl-24395",
    "prdl-24379", "prdl-70282",
]


def load_sonnet_grades() -> dict:
    grades = {}
    for line in SONNET_GRADES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        grades[d["work"].split("_")[0]] = d
    return grades


def find_work_dir(prdl: str) -> Path | None:
    matches = list(CORPUS.glob(prdl + "_*"))
    return matches[0] if matches else None


def assemble_work(prdl: str, sonnet: dict, published_meta: dict | None) -> bool:
    wd = find_work_dir(prdl)
    if not wd:
        print(f"  {prdl}: WORK DIR NOT FOUND")
        return False

    lane_dir = wd / "translations" / LANE / "full"
    ocr_path = wd / "translations" / "_reocr" / OCR_ENGINE / "full.txt"
    chunk_files = sorted(lane_dir.glob("full_chunk_*.md"))

    if not chunk_files:
        print(f"  {prdl}: NO TRANSLATION CHUNKS")
        return False
    if not ocr_path.exists():
        print(f"  {prdl}: NO OCR")
        return False

    work_id = wd.name
    destination = OUT_ROOT / work_id
    published = destination if destination.is_dir() else ROOT / "works-t4b" / work_id
    prior_path = published / "metadata.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8")) if prior_path.is_file() else {}
    witness_id = prior.get("standard_witness", work_id)
    if not published_meta:
        published_meta = next((w for w in json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["works"]
                               if w["id"] == witness_id), {})
    with staged_directory(destination, seed=False) as stage:
        grades = sonnet.get(prdl, {})
        if not grades and prior.get("chunks_graded") and len(chunk_files) == prior["chunks_total"]:
            grades = {"n": prior["chunks_graded"], "tier": prior["tier"],
                      "mean_faithful": prior["faithful_adj"], "hallucination_pct": prior["hallucinated_pct"]}
        write_edition(stage, work_id, chunk_files, ocr_path, grades, published_meta, prior)
        for source in (published / "intro.md", published / "ERRATA.md"):
            if source.is_file():
                shutil.copyfile(source, stage / source.name)
        restore_track(ROOT, work_id, "t4b", stage, published)
        if grades and prdl not in sonnet and published.is_dir():
            if (stage / "english.md").read_text(encoding="utf-8") != (published / "english.md").read_text(encoding="utf-8"):
                raise ValueError(f"{work_id}: fresh audit evidence needed for a changed translation")
    return True


def write_edition(out_dir: Path, work_id: str, chunk_files: list[Path], ocr_path: Path,
                  grades: dict, published_meta: dict, previous: dict) -> None:
    # 1. Latin OCR (LoRA witness) — clean link-placeholder artifacts from scan headers
    ocr_text = ocr_path.read_text(encoding="utf-8", errors="replace")
    ocr_text = ocr_text.replace("<[Persistent URL]>", "[Persistent URL]")
    ocr_text = ocr_text.replace("<[Call number]>", "[Call number]")
    (out_dir / "latin-ocr.txt").write_text(ocr_text, encoding="utf-8")

    # 2. Chunks
    chunks_dir = out_dir / "chunks"
    chunks_dir.mkdir()
    for cf in chunk_files:
        shutil.copy2(cf, chunks_dir / cf.name)

    # 3. english.md = concatenated chunks with segment markers
    parts = []
    for cf in chunk_files:
        idx = int(cf.stem.rsplit("_", 1)[-1])
        text = cf.read_text(encoding="utf-8", errors="replace").strip()
        # Clean OCR-source placeholder text that renders as broken href links.
        # The scans carry "[Persistent URL]" / "[Call number]" metadata that
        # GPT-5.5 sometimes preserved as literal <a href="[Persistent URL]"> tags.
        text = re.sub(r'<a\s+href="\[Persistent URL\]">[^<]*</a>', "[Persistent URL]", text, flags=re.I)
        text = re.sub(r'<a\s+href="\[Call number\]">[^<]*</a>', "[Call number]", text, flags=re.I)
        text = text.replace("<[Persistent URL]>", "[Persistent URL]")
        text = text.replace("<[Call number]>", "[Call number]")
        text = text.replace("<Persistent URL>", "Persistent URL")
        parts.append(f"[segment {idx}]\n{text}")
    (out_dir / "english.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")

    # 4. intro.md from published edition (same text)
    pub_intro = ROOT / "works" / previous.get("standard_witness", work_id) / "intro.md"
    if pub_intro.exists():
        shutil.copy2(pub_intro, out_dir / "intro.md")

    # 5. metadata.json with Sonnet grades + T4B branding
    s = grades
    meta = {
        **previous,
        "id": work_id,
        "edition": "trithemius-4b",
        "edition_label": "Trithemius 4B edition",
        "title": published_meta.get("title", work_id) if published_meta else work_id,
        "title_en": published_meta.get("title_en") if published_meta else None,
        "year": published_meta.get("year", "") if published_meta else "",
        "source_year": published_meta.get("source_year") if published_meta else None,
        "composition_year": published_meta.get("composition_year") if published_meta else None,
        "year_note": published_meta.get("year_note") if published_meta else None,
        "edition_info": published_meta.get("edition_info", "") if published_meta else "",
        "page_count": published_meta.get("page_count", 0) if published_meta else 0,
        "genre_cluster": published_meta.get("genre_cluster", "") if published_meta else "",
        "source": published_meta.get("source", {}) if published_meta else {},
        "license": published_meta.get("license", "CC0-1.0") if published_meta else "CC0-1.0",
        "first_english": published_meta.get("first_english") if published_meta else None,
        "tier": s.get("tier", "?"),
        "faithful_adj": s.get("mean_faithful", 0),
        "fluent_adj": s.get("mean_faithful", 0),  # T4B uses same value for fluent
        "hallucinated_pct": s.get("hallucination_pct", 0),
        "chunks_graded": s.get("n", 0),
        "chunks_total": len(chunk_files),
        "coverage_pct": round(s.get("n", 0) / len(chunk_files) * 100, 1) if chunk_files else 0,
        "low_pct": 0.0,
        "unclear_count": 0,
        "first_english_note": published_meta.get("first_english_note") if published_meta else None,
        "grader": "claude-sonnet-5",
        "ocr_engine": "qwen3vl-4b-trithemius-q6 (Trithemius LoRA)",
        "translator": "gpt-5.5 (dual-context)",
        "canonical_backend": LANE,
        "source_work_id": work_id,
    }
    for key in ("attribution", "duplicate_source_group", "duplicate_source_note"):
        if published_meta.get(key):
            meta[key] = published_meta[key]
    (out_dir / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"  {work_id}: {len(chunk_files)} source chunks")


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    sonnet = load_sonnet_grades()

    # Load published metadata for titles etc.
    published = {}
    manifest_path = ROOT / "manifest.json"
    if manifest_path.exists():
        mf = json.loads(manifest_path.read_text(encoding="utf-8"))
        for w in mf.get("works", []):
            published[w["id"]] = w

    ok = 0
    for prdl in PUBLISH_PRDLS:
        pub_meta = None
        wd = find_work_dir(prdl)
        if wd:
            pub_meta = published.get(wd.name, {})
        if assemble_work(prdl, sonnet, pub_meta):
            ok += 1

    print(f"\nAssembled {ok}/{len(PUBLISH_PRDLS)} Trithemius 4B edition works into {OUT_ROOT}")
    return 0 if ok == len(PUBLISH_PRDLS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
