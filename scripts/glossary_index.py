"""Latin->English domain glossary, injected per chunk into the prompt.

This is distinct from data/prompts/_named_entities.md (proper nouns) and from
the short term lists in _base.md / the cluster prompts. It is a ~160-entry
lexicon of the *false-friend* and technical-vocabulary traps that the bulk
translator (MiniMax) fumbles inconsistently — `religio` (the Order, not
modern 'religion'), `conversatio` (manner of life, not 'conversation'),
`saeculum` (the world/age), `ruina` (ruin, not 'decline'), the cipher senses
of `spiritus`/`angelus`/`clavis`, etc.

Like the Vulgate detector it is *dynamic*: only the entries whose surface
forms actually occur in a given chunk are injected, so the prompt stays
small and the guidance is always relevant. Off unless --use-glossary.

EVALUATED 2026-05-17: a 15-chunk smoke (→ minimax-v3, inline-graded) showed
NO measurable grade lift — mean Δ adjusted-faithful −0.02 (sacerdotal S) and
+0.04 (devotional A) across clean chunks; the per-chunk ±0.9 swings are
one-bucket MiniMax grader noise, not glossary signal. The full sweep was
therefore NOT run (no quality gain, plus a blanket re-translation would
destroy the curated OCR-untranslatable placeholders). This file is retained
as a curated scholarly Latin→English domain lexicon (useful as a data
resource in its own right) and as correct opt-in infrastructure — it is not
a proven grader-mover. Note also the MM→Opus calibration ceiling (~4.4):
no MiniMax-graded re-translation can reach an "S+ ≥4.5" tier.

    from glossary_index import GlossaryIndex
    gi = GlossaryIndex.load("monastic-reform")
    hits = gi.match(latin_chunk_text)          # [{lemma, en, note}, ...]
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GLOSSARY_PATH = REPO / "data" / "lexicon" / "glossary.jsonl"


def _norm(text: str) -> str:
    """Light OCR-tolerant fold for matching only (not for output): long-s,
    ligatures, u/v and i/j unification, punctuation -> space, lowercase."""
    t = text.lower()
    for a, b in (("ſ", "s"), ("æ", "ae"), ("œ", "oe"), ("ſ", "s")):
        t = t.replace(a, b)
    t = t.replace("j", "i").replace("v", "u")
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


class GlossaryIndex:
    def __init__(self, entries: list[dict]) -> None:
        # Pre-normalise each surface form once; longest-first so multi-word
        # phrases ("conversatio morum") win over their parts.
        self._entries = []
        for e in entries:
            forms = sorted({_norm(f) for f in e.get("forms", [])}, key=len, reverse=True)
            if forms:
                self._entries.append({**e, "_forms": forms})

    @classmethod
    def load(cls, cluster: str | None = None) -> "GlossaryIndex":
        rows = []
        for line in GLOSSARY_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            cl = r.get("clusters", "all")
            ok = cl == "all" or (isinstance(cl, list) and (cluster in cl or "all" in cl))
            if cluster is None or ok:
                r["_cluster_specific"] = isinstance(cl, list) and cluster in cl
                rows.append(r)
        return cls(rows)

    def match(self, latin_text: str, max_hits: int = 14) -> list[dict]:
        hay = " " + _norm(latin_text) + " "
        hits: list[dict] = []
        seen: set[str] = set()
        for e in self._entries:
            if e["lemma"] in seen:
                continue
            for f in e["_forms"]:
                if f and f" {f} " in hay:
                    hits.append({
                        "lemma": e["lemma"],
                        "en": e["en"],
                        "note": e.get("note", ""),
                        "_cs": bool(e.get("_cluster_specific")),
                        "_len": len(f),
                    })
                    seen.add(e["lemma"])
                    break
        # Cluster-specific terms first, then longer (more specific) matches.
        hits.sort(key=lambda h: (not h["_cs"], -h["_len"]))
        out = [{"lemma": h["lemma"], "en": h["en"], "note": h["note"]}
               for h in hits[:max_hits]]
        return out


def render_block(hits: list[dict]) -> str:
    """Prompt fragment. Empty string when nothing matched."""
    if not hits:
        return ""
    lines = ["Translation glossary — for the Latin terms below that occur in "
             "this passage, use the given English rendering and heed the note:"]
    for h in hits:
        n = f" — {h['note']}" if h.get("note") else ""
        lines.append(f"- {h['lemma']} = {h['en']}{n}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    gi = GlossaryIndex.load(sys.argv[1] if len(sys.argv) > 1 else None)
    print(render_block(gi.match(sys.stdin.read())))
