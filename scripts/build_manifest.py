"""Refresh manifest.json from committed release artifacts.

The public release source of truth is the checked-in per-work metadata under
`works/<id>/metadata.json`. This script keeps root `manifest.json` aligned with
those files while preserving manifest-only fields such as priority, title_en,
unclear counts, skipped source records, and calibration notes.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.json"
WORKS = ROOT / "works"
WORK_TITLES = ROOT / "work_titles.json"

RELEASE_LICENSE = (
    "CC-BY-4.0 for documentation/code/arrangement; "
    "CC0-1.0 for generated translation artifacts (see LICENSE)"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = load_json(MANIFEST)
    titles = load_json(WORK_TITLES) if WORK_TITLES.exists() else {}
    metadata_by_id = {
        p.parent.name: load_json(p)
        for p in sorted(WORKS.glob("prdl-*/metadata.json"))
    }

    refreshed: list[dict] = []
    for entry in manifest.get("works", []):
        if entry.get("skip"):
            refreshed.append(entry)
            continue

        wid = entry["id"]
        meta = metadata_by_id.get(wid)
        if meta is None:
            short = wid.split("_", 1)[0]
            candidates = [m for k, m in metadata_by_id.items() if k.startswith(short + "_")]
            if len(candidates) == 1:
                meta = candidates[0]
        if meta is None:
            raise SystemExit(f"missing works metadata for {wid}")

        row = dict(entry)
        for key in [
            "id",
            "title",
            "year",
            "source_year",
            "year_note",
            "edition_info",
            "edition_info_raw",
            "duplicate_source_group",
            "duplicate_source_note",
            "page_count",
            "genre_cluster",
            "tier",
            "faithful_adj",
            "fluent_adj",
            "coverage_pct",
            "chunks_graded",
            "chunks_total",
            "hallucinated_pct",
            "low_pct",
            "canonical_backend",
            "all_backends",
            "source",
            "license",
        ]:
            if key in meta:
                row[key] = meta[key]
        row["skip"] = False
        row["skip_reason"] = ""
        row["title"] = titles.get(row["id"], {}).get("title", row.get("title"))
        row["title_en"] = titles.get(row["id"], {}).get("title_en", row.get("title_en"))
        row.setdefault("preamble_pct", 0.0)
        refreshed.append(row)

    manifest["works"] = refreshed
    manifest["total_works"] = len(refreshed)
    manifest["translatable_works"] = sum(1 for w in refreshed if not w.get("skip"))
    manifest["skipped_works"] = sum(1 for w in refreshed if w.get("skip"))
    manifest["license"] = RELEASE_LICENSE

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    tiers = {k: 0 for k in "SABCF"}
    chunks_total = 0
    chunks_graded = 0
    for work in refreshed:
        if work.get("skip"):
            continue
        tiers[work.get("tier", "F")] = tiers.get(work.get("tier", "F"), 0) + 1
        chunks_total += int(work.get("chunks_total") or 0)
        chunks_graded += int(work.get("chunks_graded") or 0)

    print(f"wrote {MANIFEST.relative_to(ROOT)}")
    print(f"  works: {manifest['translatable_works']} translatable + {manifest['skipped_works']} skipped")
    print(
        "  tiers: "
        + " ".join(f"{tier}={tiers.get(tier, 0)}" for tier in ["S", "A", "B", "C", "F"])
    )
    print(f"  chunks: {chunks_total} total / {chunks_graded} graded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
