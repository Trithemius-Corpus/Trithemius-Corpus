r"""Phase 3b — generate fact-constrained DRAFT per-work intro essays.

Writes `works/<id>/intro.draft.md` (NOT intro.md) for every translatable work
that lacks a finished intro. Drafts are deliberately conservative: the model
is given only (a) the manifest facts for that work, (b) the universally
established Trithemius frame already stated in TEMPLATE_intro.md, and (c) a
short prose excerpt from the shipping translation. It is instructed to use the
template's placeholder sentence rather than invent dates, dedicatees, or
claims about other translators' editions — those require real research and the
prior-session research notes did not survive. Drafts are queued for an Opus
enrichment/verification pass after the quality sweep frees the Claude window;
nothing here is promoted to intro.md automatically.

Runs on MiniMax (bulk lane) so it is safe to run while the single Opus sweep
worker is active.

Usage:
    python scripts/build_intro_drafts.py                 # all missing
    python scripts/build_intro_drafts.py --only prdl-24360_...   # one work
    python scripts/build_intro_drafts.py --limit 5       # first N (smoke)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKING = Path(r"E:\trithemius")
CORPUS = WORKING / "data" / "corpus"
MANIFEST = REPO / "manifest.json"
WORKS_DIR = REPO / "works"
TEMPLATE = REPO / "docs" / "TEMPLATE_intro.md"

# Reuse the working repo's MiniMax key loader + rate limiter.
sys.path.insert(0, str(WORKING / "scripts"))
from minimax_self_grade import _load_minimax_key, _rate_limit  # noqa: E402

# Well-established, citation-safe one-liners per cluster. These say only what
# the corpus's own METHODOLOGY/README already assert; no dates or judgments.
CLUSTER_CONTEXT = {
    "crypto-occult": "part of Trithemius's cryptographic and steganographic project (the tradition of the *Steganographia* and *Polygraphia*)",
    "bibliographic": "part of Trithemius's bibliographical and ecclesiastical-history work (the tradition of *De Scriptoribus Ecclesiasticis*)",
    "monastic-reform": "a Benedictine monastic-reform writing from Trithemius's career as a reforming abbot",
    "sacerdotal": "a work on priestly life and clerical formation",
    "marian-hagiographic": "a Marian and hagiographic work (the *De Laudibus* tradition, much of it on St Anne)",
    "devotional": "a devotional and contemplative work",
    "apologetic": "an apologetic and self-defensive work answering Trithemius's critics",
    "verse": "a verse composition",
}

SYSTEM = (
    "You are a careful scholarly editor writing a short headnote for a public "
    "corpus of Johannes Trithemius (1462-1516; abbot of Sponheim until 1505, "
    "then of the Schottenkloster at Wurzburg). You write only what is given to "
    "you. You never invent dates, dedicatees, printing history, or claims about "
    "whether another English translation exists. When a fact is not supplied, "
    "you fall back to the supplied placeholder sentence. Plain prose, 80-150 "
    "words, one or two paragraphs. Italicise Latin titles with *asterisks*."
)


def minimax_chat(system: str, user: str, timeout: int = 120, max_retries: int = 4) -> str:
    api_key = _load_minimax_key()
    payload = {
        "model": "MiniMax-M2.7",
        "max_tokens": 2400,  # generous: thinking budget + ~200-word essay
        "temperature": 0.4,
        "top_p": 0.8,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    body = json.dumps(payload).encode("utf-8")
    last = None
    for attempt in range(max_retries):
        try:
            _rate_limit()
            req = urllib.request.Request(
                "https://api.minimax.io/anthropic/v1/messages",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            parts = [c.get("text", "") for c in (data.get("content") or []) if c.get("type") == "text"]
            text = "\n".join(parts).strip()
            if not text:
                raise RuntimeError(f"empty content (stop={data.get('stop_reason')})")
            return text
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt + 1 < max_retries:
                wait = min(30, 5 * (2 ** attempt))
                print(f"  [intro] retry {attempt+1}/{max_retries} after {wait}s: {e}", flush=True)
                time.sleep(wait)
    raise RuntimeError(f"minimax failed after {max_retries}: {last}")


def prose_excerpt(work_id: str, max_chars: int = 700) -> str:
    """A mid-document prose chunk from the shipping public backend, if any."""
    full = CORPUS / work_id / "translations" / "public" / "full"
    if not full.is_dir():
        return ""
    chunks = sorted(full.glob("full_chunk_*.md"))
    if not chunks:
        return ""
    for cand in (chunks[len(chunks) // 4], chunks[len(chunks) // 2], chunks[0]):
        txt = cand.read_text(encoding="utf-8", errors="replace").strip()
        if txt.startswith("<!--") or len(txt) < 120:
            continue
        return txt[:max_chars]
    return ""


def load_template_rules() -> str:
    return TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else ""


def exemplars() -> str:
    out = []
    for d in sorted(WORKS_DIR.iterdir()):
        f = d / "intro.md"
        if d.is_dir() and f.exists():
            out.append(f"--- exemplar ({d.name}) ---\n{f.read_text(encoding='utf-8').strip()}")
        if len(out) == 2:
            break
    return "\n\n".join(out)


def build_prompt(work: dict, rules: str, exes: str) -> str:
    cl = work.get("genre_cluster")
    pack = {
        "title_raw": work.get("title"),
        "year": work.get("year"),
        "edition_info": work.get("edition_info"),
        "page_count": work.get("page_count"),
        "genre_cluster": cl,
        "cluster_context": CLUSTER_CONTEXT.get(cl, "part of Trithemius's corpus"),
        "tier": work.get("tier"),
        "faithful_adj": work.get("faithful_adj"),
        "canonical_backend": work.get("canonical_backend"),
        "source": work.get("source"),
    }
    placeholder = (
        f"*Intro essay pending. This work is {pack['cluster_context']}. "
        f"See the source-provenance link above for the original edition.*"
    )
    excerpt = prose_excerpt(work["id"])
    return (
        f"TEMPLATE RULES (obey exactly):\n{rules}\n\n"
        f"TWO EXEMPLAR INTROS (match this register, not their specific facts):\n{exes}\n\n"
        f"DATA PACK for the work you must write (the ONLY work-specific facts "
        f"you may state):\n{json.dumps(pack, indent=1, ensure_ascii=False)}\n\n"
        f"PROSE EXCERPT from the shipping translation (for tone/subject only — "
        f"do not quote it verbatim):\n<<<\n{excerpt or '(none available)'}\n>>>\n\n"
        f"HARD RULES:\n"
        f"- Use ONLY the data pack + the established Trithemius frame in the "
        f"system message. Do NOT invent a date, dedicatee, occasion, or "
        f"printing history not in the pack.\n"
        f"- Do NOT state or deny that an English translation exists elsewhere "
        f"(that needs research not provided). You MAY note this corpus's tier "
        f"and that it is a Latin->English rendering.\n"
        f"- If you cannot write a confident, fact-grounded headnote, output "
        f"EXACTLY this placeholder and nothing else:\n{placeholder}\n"
        f"- 80-150 words. Output only the headnote markdown. No preamble, no "
        f"heading, no code fence."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--overwrite-drafts", action="store_true",
                    help="Regenerate even if intro.draft.md already exists.")
    args = ap.parse_args()

    works = [w for w in json.loads(MANIFEST.read_text(encoding="utf-8"))["works"]
             if not w.get("skip")]
    rules, exes = load_template_rules(), exemplars()

    todo = []
    for w in works:
        wd = WORKS_DIR / w["id"]
        if (wd / "intro.md").exists():
            continue
        if (wd / "intro.draft.md").exists() and not args.overwrite_drafts:
            continue
        if args.only and w["id"] != args.only:
            continue
        todo.append(w)
    if args.limit:
        todo = todo[: args.limit]

    print(f"intro drafts to generate: {len(todo)}")
    done = 0
    for i, w in enumerate(todo, 1):
        wd = WORKS_DIR / w["id"]
        wd.mkdir(parents=True, exist_ok=True)
        try:
            text = minimax_chat(SYSTEM, build_prompt(w, rules, exes))
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(todo)}] FAIL {w['id']}: {e}", flush=True)
            continue
        header = (
            f"<!-- DRAFT intro generated by build_intro_drafts.py (MiniMax). "
            f"Needs Opus verification/enrichment before promotion to intro.md. -->\n\n"
        )
        (wd / "intro.draft.md").write_text(header + text.strip() + "\n", encoding="utf-8")
        done += 1
        print(f"[{i}/{len(todo)}] wrote {w['id']}/intro.draft.md ({len(text)} chars)", flush=True)
    print(f"done: {done}/{len(todo)} drafts written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
