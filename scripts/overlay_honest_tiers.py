"""Overlay the honest GPT-5.5 tier (from scoreboard_gpt_v3.csv) onto each
work's entry in manifest.json. build_manifest.py predates the independent
GPT-5.5 audit and still pulls tiers from the original MiniMax-calibrated
ledger; until that script is rewritten, this overlay keeps manifest.json
internally consistent with README.md and METHODOLOGY.md.

For each work in manifest.json that has a tier:
  * Look up the work in scoreboard_gpt_v3.csv (by work_id).
  * Replace `tier` with the honest tier (S/A/B/C/F or U).
  * Add `tier_source = "gpt55_v3"` and `tier_legacy_minimax = <old tier>`
    for provenance.
  * Refresh `faithful_mean`, `hallucinated_pct`, `ge4_clean_pct` from the
    GPT-5.5 row.

Idempotent.

    python scripts/overlay_honest_tiers.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.json"
SCOREBOARD = ROOT / "data" / "_quality" / "scoreboard_gpt_v3.csv"


def main() -> int:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sb = {r["work_id"]: r for r in
          csv.DictReader(SCOREBOARD.open(encoding="utf-8"))}
    works = m.get("works") if isinstance(m, dict) else m
    if isinstance(works, dict):
        items = works.items()
    else:
        items = ((w.get("id"), w) for w in works)
    updated = unchanged = unmatched = 0
    for wid, w in items:
        s = sb.get(wid)
        if not s:
            unmatched += 1
            continue
        legacy = w.get("tier")
        new_tier = s["honest_tier"]
        if legacy and legacy != new_tier:
            w["tier_legacy_minimax"] = legacy
        w["tier"] = new_tier
        w["tier_source"] = "gpt55_v3"
        try:
            w["faithful_mean"] = float(s["faith_gpt"]) if s["faith_gpt"] else None
            w["hallucinated_pct"] = float(s["hall_pct"]) if s["hall_pct"] else None
            w["ge4_clean_pct"] = float(s["ge4_clean_pct"]) if s["ge4_clean_pct"] else None
            # Works added after the original build_manifest grade pass (e.g. the
            # Steganographia, graded via the reocr path) have no faithful_adj from
            # build_manifest; backfill the template fields from the scoreboard so
            # the build is reproducible.
            if w.get("faithful_adj") is None and s["faith_gpt"]:
                w["faithful_adj"] = float(s["faith_gpt"])
                w["fluent_adj"] = w.get("fluent_adj") or float(s["faith_gpt"])
                n = int(s["n"]) if s.get("n") else None
                w["chunks_graded"] = w.get("chunks_graded") or n
                w["chunks_total"] = w.get("chunks_total") or n
                w["coverage_pct"] = w.get("coverage_pct") or 100.0
                w["preamble_pct"] = w.get("preamble_pct") or 0.0
                w["low_pct"] = w.get("low_pct") or 0.0
        except (ValueError, KeyError):
            pass
        if legacy != new_tier:
            updated += 1
        else:
            unchanged += 1
    MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    import collections
    tiers = collections.Counter()
    iterable = m.get("works") if isinstance(m.get("works"), list) else \
               (m["works"].values() if isinstance(m.get("works"), dict) else m)
    for w in iterable:
        if isinstance(w, dict) and w.get("tier"):
            tiers[w["tier"]] += 1
    print(f"manifest.json overlay: {updated} tier changes, {unchanged} same, "
          f"{unmatched} unmatched")
    print(f"  honest tiers in manifest now: {dict(sorted(tiers.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
