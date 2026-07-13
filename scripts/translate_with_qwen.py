"""Translate a chunked work's full.txt from Latin to English using a local
Qwen3-VL-4B llama-server in /v1/chat/completions mode.

Why a dedicated driver instead of latin_translation_harness.py:
- The harness hard-codes the Gemma chat template on the /completion endpoint
  (latin_translation_harness.py:554-559). Qwen3-VL uses <|im_start|>, so we
  need /v1/chat/completions which auto-applies the GGUF's embedded Jinja.

This driver is intentionally minimal:
- One system message (Latin -> English translation guidance)
- One user message with the Latin OCR text
- Page markers are preserved in the input and expected in the output

Outputs go to translations/<out_backend>/full/full_chunk_NNNN.md with a
runs.jsonl line per chunk for parity with codex's translator output.

Usage:
    python scripts/translate_with_qwen.py \
        --work prdl-24376_ecloga-de-laude-calvorum-ad-carolum \
        --server-url http://127.0.0.1:8080 \
        --out-backend qwen3vl-trithemius-q6-translator-qwen \
        --max-chars 4500
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from retrieve_examples import cluster_of_work, retrieval_for_cluster  # noqa: E402
from v3_output_guards import validate_translation_output  # noqa: E402

PAGE_MARKER_RE = re.compile(r"^---\s*Page\s+\d+\s*---\s*$", re.M)

# System prompt intentionally terse. The Qwen3-VL-4B-Trithemius LoRA was
# fine-tuned on (latin_ocr, english_translation) pairs in the standard
# Qwen chat format; a long system prompt can pull the model off the
# distribution it was trained on. The system prompt does the four things
# the model needs to know: (1) the task, (2) preserve page markers, (3)
# do not invent content, (4) output the translation directly with no
# preamble. Everything else (OCR normalization) the model handles because
# it was trained on noisy OCR input.
SYSTEM_PROMPT = """You translate early-modern Latin into clear scholarly English.

Output the English translation directly. Do not write "Here is the translation", "Below is", "Translation:", or any preamble — your first character must be the first letter of the English text.

Preserve page markers ("--- Page NNN ---") exactly as they appear in the source.

Preserve all proper names, dates, and book or chapter references verbatim.

If a word or phrase is illegible in the source, mark it inline as [unclear] — do not invent content to fill gaps."""

# Page marker detection (matches the OCR output format)
PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)


def _split_long_page(page_num: int, body: str, max_chars: int) -> list[str]:
    """Split a single page body that exceeds max_chars into sub-page chunks.

    Used when one OCR page is itself too large for the NPU context window
    (304 pages in the corpus exceed 4000 chars on a single page). We split at
    paragraph boundaries (blank lines) first, then fall back to sentence
    boundaries, so the model still gets coherent context.

    Returns a list of body pieces (without the page marker). Each piece is
    <= max_chars when the input has paragraph or sentence breaks. A piece that
    is a single unsplittable run (no breaks at all) is returned over-budget;
    the short-output guard downstream refuses to cache its translation if the
    model truncates it, so such chunks retry on the next pass rather than
    ship broken.
    """
    marker_len = len(f"--- Page {page_num:03d} ---\n")
    budget = max_chars - marker_len
    if len(body) <= budget:
        return [body]
    pieces: list[str] = []
    # Try paragraph boundaries first
    paras = re.split(r"\n\s*\n", body)
    if len(paras) > 1:
        cur = ""
        for para in paras:
            cand = (cur + "\n\n" + para) if cur else para
            if len(cand) > budget and cur:
                pieces.append(cur)
                cur = para
            else:
                cur = cand
        if cur:
            pieces.append(cur)
    else:
        # Fall back to sentence boundaries
        sents = re.split(r"(?<=[.!?])\s+", body)
        if len(sents) > 1:
            cur = ""
            for sent in sents:
                cand = (cur + " " + sent) if cur else sent
                if len(cand) > budget and cur:
                    pieces.append(cur)
                    cur = sent
                else:
                    cur = cand
            if cur:
                pieces.append(cur)
        else:
            # Unsplittable run (no paragraph or sentence breaks) — return as
            # one piece even though it exceeds budget. The short-output guard
            # downstream handles any truncation; do NOT recurse.
            return [body]
    # One pass of sentence-splitting on any piece still over budget (a giant
    # paragraph). Bounded — we never recurse on the result, so unsplittable
    # runs just pass through over-budget.
    final: list[str] = []
    for p in pieces:
        if len(p) <= budget:
            final.append(p)
            continue
        sents = re.split(r"(?<=[.!?])\s+", p)
        if len(sents) <= 1:
            final.append(p)  # still unsplittable; guard handles it
            continue
        cur = ""
        for sent in sents:
            cand = (cur + " " + sent) if cur else sent
            if len(cand) > budget and cur:
                final.append(cur)
                cur = sent
            else:
                cur = cand
        if cur:
            final.append(cur)
    return final or [body]


def chunk_text(text: str, max_chars: int) -> list[tuple[list[int], str]]:
    """Split full.txt into chunks of <= max_chars at page boundaries.

    Returns list of (page_numbers, chunk_text). The Latin OCR uses
    '--- Page NNN ---' as page boundaries; we never split inside a page
    unless a single page itself exceeds max_chars, in which case
    `_split_long_page` cuts it at paragraph/sentence boundaries (each
    sub-piece keeps the same page number so markers round-trip).
    """
    # Split on page markers but keep them
    parts = re.split(r"(^---\s*Page\s+\d+\s*---\s*$)", text, flags=re.M)
    # parts alternates: [pre, marker, body, marker, body, ...]
    pages: list[tuple[int, str]] = []
    current_page = 0
    current_body = ""
    i = 0
    if parts and parts[0].strip() == "":
        i = 1
    while i < len(parts):
        marker = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        m = re.match(r"^---\s*Page\s+0*(\d+)\s*---\s*$", marker)
        if m:
            current_page = int(m.group(1))
            current_body = body
        else:
            # Pre-marker text (rare): attach to page 0
            current_body = marker + "\n" + body
        # If the body is non-empty, push
        if current_body.strip():
            pages.append((current_page, current_body))
        i += 2
    # Group pages into chunks under max_chars, never splitting a page
    chunks: list[tuple[list[int], str]] = []
    cur_pages: list[int] = []
    cur_text = ""
    for pn, body in pages:
        # Re-attach the page marker for the first page in the chunk
        marker = f"--- Page {pn:03d} ---\n"
        candidate_body = (cur_text + "\n" if cur_text else "") + marker + body
        if len(candidate_body) > max_chars and cur_pages:
            chunks.append((cur_pages, cur_text))
            cur_pages = [pn]
            cur_text = marker + body
        else:
            cur_pages.append(pn)
            cur_text = candidate_body
    if cur_pages:
        chunks.append((cur_pages, cur_text))
    # Second pass: any chunk still over max_chars (a single oversize page)
    # gets sub-split at paragraph/sentence boundaries.
    expanded: list[tuple[list[int], str]] = []
    for pns, ctext in chunks:
        if len(ctext) <= max_chars:
            expanded.append((pns, ctext))
            continue
        # ctext starts with a "--- Page N ---" marker; recover the page body
        m = re.match(r"^---\s*Page\s+0*(\d+)\s*---\s*\n", ctext)
        pn = int(m.group(1)) if m else (pns[0] if pns else 0)
        body = ctext[m.end():] if m else ctext
        for piece in _split_long_page(pn, body, max_chars):
            expanded.append(([pn], f"--- Page {pn:03d} ---\n" + piece))
    return expanded


def retrieval_query_text(chunk_text_value: str, max_chars: int = 1000) -> str:
    """Strip page markers and cap length for use as an embedding query.

    The retrieval index embeds single register-representative sentences; a
    4500-char chunk with page-marker noise is not a representative query, so
    we take a short, marker-free excerpt instead. Translation still uses the
    full chunk_text_value unchanged.
    """
    stripped = PAGE_MARKER_RE.sub("", chunk_text_value).strip()
    return stripped[:max_chars]


def build_retrieval_block(work_id: str, chunk_text_value: str, k: int,
                           use_npu: bool = False) -> tuple[str, list[str]]:
    """Return (prompt_block, refs) for the top-k cluster exemplars, or
    ("", []) if the work has no assigned cluster or nothing scores above
    the retrieval index's min_score threshold.

    Exemplars are prepended BEFORE the unchanged "Translate this Latin into
    English:" instruction (see translate_with_qwen.py module docstring) so
    the final instruction the LoRA sees is byte-identical to what it was
    fine-tuned on -- only reference material is added ahead of it.

    EVALUATED 2026-07-05, NO-GO (see glossary_index.py for the sibling
    experiment that also failed, and the same discipline applied here).
    Two findings from a 15-chunk paired smoke test on
    prdl-24373_de-statu-et-ruina-monastici-ordinis (monastic-reform
    cluster), MiniMax-M3 graded against the SAME chunks with retrieval off:
      1. At the production --ctx-len 2048, injecting even k=2 exemplars
         (~200 extra tokens) collided with an already-thin context budget:
         10/15 chunks truncated, 2/15 outright failed (HTTP 400), vs.
         ok=15/15 with no retrieval at the same ctx-len. The baseline
         prompt was already using ~1263 of 2048 tokens before generation.
      2. Raising --ctx-len to 3072 fixes the crashing (ok=15/15 both
         conditions) but retrieval still does not help quality: mean
         faithful dropped 2.00 -> 1.73, fluent flat (2.07 -> 2.00),
         hallucination rate unchanged within noise (13/15 -> 12/15). No
         chunk showed a clear win. Full grades:
         data/corpus/_quality/retrieval_smoketest_grades.jsonl (trithemius
         working repo).
    Do not re-enable this flag for corpus-wide use without a materially
    different injection strategy (different exemplar shape, different k,
    or a different retrieval signal) -- re-running the same mechanism is
    not expected to change the outcome, per [[reference_glossary_sweep_negative]].
    """
    cluster = cluster_of_work(work_id)
    if not cluster:
        return "", []
    try:
        ri = retrieval_for_cluster(cluster, use_npu=use_npu)
    except FileNotFoundError:
        return "", []
    query = retrieval_query_text(chunk_text_value)
    if not query:
        return "", []
    examples = ri.retrieve(query, k=k)
    if not examples:
        return "", []
    lines = ["Reference translations (same genre/register -- for terminology "
             "and tone guidance only; do not copy verbatim):", ""]
    for ex in examples:
        lines.append(f"Latin: {ex['latin']}")
        lines.append(f"English: {ex['english']}")
        lines.append("")
    return "\n".join(lines), [ex["ref"] for ex in examples]


def call_chat(server_url: str, system: str, user: str,
              max_tokens: int, temperature: float, top_p: float,
              timeout: int, model: str = "") -> str:
    """POST to /v1/chat/completions. Returns the assistant message text.

    `model` is sent in the payload so FLM routes to the requested tag. If empty,
    no model field is sent and the server uses its default (which may not be the
    LoRA fine-tune -- always pass the explicit tag for production).
    """
    payload = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": False,
    }
    if model:
        payload["model"] = model
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        server_url.rstrip("/") + "/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, help="Work id (folder name under data/corpus/)")
    ap.add_argument("--server-url", default="http://127.0.0.1:8080")
    ap.add_argument("--model", default="qwen3vl-trithemius:4b",
                    help="Model tag sent in the chat payload. MUST match a tag the "
                         "server is actually serving -- FLM routes by this field and "
                         "silently falls back to its default model if omitted, which "
                         "is how the base qwen3vl-it:4b ended up being used instead "
                         "of the Trithemius LoRA.")
    ap.add_argument("--out-backend", required=True,
                    help="Subdir name under data/corpus/<work>/translations/")
    ap.add_argument("--ocr-engine", default="qwen3vl-4b-trithemius-q6",
                    help="Engine name of the OCR witness (matches _reocr/<engine>/)")
    ap.add_argument("--max-chars", type=int, default=4500,
                    help="Max Latin chars per chunk (pages longer than this are "
                         "sub-split at paragraph/sentence boundaries)")
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--top-p", type=float, default=0.6)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--max-chunks", type=int, default=0,
                    help="0 = all chunks; positive N = first N only (smoke test)")
    ap.add_argument("--force", action="store_true",
                    help="Re-translate even if chunk file exists")
    ap.add_argument("--retry-short", action="store_true",
                    help="Re-translate existing chunks whose output is suspiciously "
                         "short (<35%% of input) -- the signature of NPU context "
                         "truncation. Use to reclaim the pre-fix backlog without "
                         "deleting files by hand.")
    ap.add_argument("--short-ratio", type=float, default=0.35,
                    help="Output/input ratio below which a chunk is considered "
                         "truncated (Latin->English expansion is ~1.1-1.4x, so "
                         "anything under 0.35x is a cutoff). Default 0.35.")
    ap.add_argument("--use-retrieval", action="store_true",
                    help="EVALUATED 2026-07-05, NO-GO -- see build_retrieval_block() "
                         "docstring in this file for the full smoke-test results "
                         "(context-budget crashes at ctx-len 2048; no quality lift "
                         "even once that's fixed at ctx-len 3072). Kept as opt-in "
                         "infrastructure, not recommended for corpus-wide use.")
    ap.add_argument("--retrieval-k", type=int, default=2,
                    help="Number of exemplars to inject when --use-retrieval is set. "
                         "Kept small (default 2) since the LoRA was fine-tuned on a "
                         "short, plain prompt -- see module docstring.")
    ap.add_argument("--retrieval-encoder", choices=["cpu", "npu"], default="cpu",
                    help="cpu = sentence-transformers MiniLM index (data/retrieval/, "
                         "no extra process dependency). npu = embed-gemma:300m via "
                         "FLM (data/retrieval_npu/); requires FLM running with "
                         "--embed 1 and the index built with "
                         "build_retrieval_index_npu.py. Only matters if "
                         "--use-retrieval is set.")
    ap.add_argument("--strict-output-guards", action="store_true",
                    help="Refuse to cache chunks with marker drift/drop, preambles, "
                         "loops, or enabled anchor failures.")
    ap.add_argument("--require-source-anchor", action="store_true",
                    help="Require at least one source proper-name/numeric anchor to "
                         "survive in each translated chunk.")
    args = ap.parse_args()

    work_dir = CORPUS / args.work
    if not work_dir.is_dir():
        raise SystemExit(f"Work dir not found: {work_dir}")
    full_txt = work_dir / "translations" / "_reocr" / args.ocr_engine / "full.txt"
    if not full_txt.is_file():
        raise SystemExit(f"OCR full.txt not found: {full_txt}")
    latin = full_txt.read_text(encoding="utf-8", errors="replace")
    print(f"[{args.work}] loaded OCR: {len(latin)} chars from {full_txt}")

    out_dir = work_dir / "translations" / args.out_backend / "full"
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_path = out_dir / "runs.jsonl"

    chunks = chunk_text(latin, args.max_chars)
    print(f"[{args.work}] {len(chunks)} chunks (max_chars={args.max_chars})")
    if args.max_chunks:
        chunks = chunks[: args.max_chunks]
        print(f"[{args.work}] truncated to {len(chunks)} chunks (--max-chunks)")

    n_ok = 0
    n_skip = 0
    n_fail = 0
    n_short = 0
    n_guard = 0
    n_retried = 0
    t0 = time.time()
    for idx, (pages, chunk_text_value) in enumerate(chunks, start=1):
        out_path = out_dir / f"full_chunk_{idx:04d}.md"
        if out_path.exists() and not args.force:
            if args.retry_short:
                # Reclaim a pre-fix truncated chunk: if the existing output is
                # suspiciously short vs. its input, retranslate it in place.
                existing = out_path.read_text(encoding="utf-8", errors="replace")
                if len(chunk_text_value) > 0 and \
                   len(existing) < len(chunk_text_value) * args.short_ratio:
                    n_retried += 1
                    print(f"  [{idx}/{len(chunks)}] retry-short "
                          f"(existing {len(existing)}c < {len(chunk_text_value)}c*{args.short_ratio:.2f})")
                    # fall through to retranslate
                else:
                    n_skip += 1
                    continue
            else:
                n_skip += 1
                print(f"  [{idx}/{len(chunks)}] skip (exists): {out_path.name}")
                continue
        retrieval_refs: list[str] = []
        retrieval_block = ""
        if args.use_retrieval:
            retrieval_block, retrieval_refs = build_retrieval_block(
                args.work, chunk_text_value, args.retrieval_k,
                use_npu=(args.retrieval_encoder == "npu"))
        user_msg = (
            f"{retrieval_block}Translate this Latin into English:\n\n{chunk_text_value}"
            if retrieval_block else
            f"Translate this Latin into English:\n\n{chunk_text_value}"
        )
        t_chunk = time.time()
        try:
            english = call_chat(
                args.server_url, SYSTEM_PROMPT, user_msg,
                args.max_tokens, args.temperature, args.top_p, args.timeout,
                args.model,
            )
        except Exception as exc:
            n_fail += 1
            print(f"  [{idx}/{len(chunks)}] FAIL pages={pages}: {type(exc).__name__}: {exc}")
            continue
        elapsed = time.time() - t_chunk
        # Short-output guard: refuse to cache a truncated translation. Latin->
        # English expands ~1.1-1.4x; a result under short_ratio of the input
        # length is a context-window cutoff, not a translation. Leave any
        # existing file untouched (so a prior good translation survives) and
        # log the short result so the next pass retries it.
        if len(chunk_text_value) > 0 and \
           len(english) < len(chunk_text_value) * args.short_ratio:
            n_short += 1
            print(f"  [{idx}/{len(chunks)}] SHORT pages={pages} "
                  f"latin={len(chunk_text_value)} english={len(english)} "
                  f"(ratio {len(english)/len(chunk_text_value):.2f} < {args.short_ratio}) "
                  f"-- not cached, will retry next pass {elapsed:.1f}s")
            with runs_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "chunk": idx,
                    "pages": pages,
                    "input_chars": len(chunk_text_value),
                    "output_chars": len(english),
                    "elapsed_seconds": round(elapsed, 2),
                    "engine": args.ocr_engine,
                    "translator": "qwen3vl-4b-trithemius-q6",
                    "model": args.model,
                    "warn": "short_output",
                    "retrieval_refs": retrieval_refs,
                    "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                }, ensure_ascii=False) + "\n")
            continue
        guard = validate_translation_output(
            output_text=english,
            expected_pages=pages,
            source_text=chunk_text_value,
            require_source_anchor=args.require_source_anchor,
        )
        if args.strict_output_guards and guard["blocking_issues"]:
            n_guard += 1
            print(f"  [{idx}/{len(chunks)}] GUARD pages={pages} "
                  f"issues={','.join(guard['blocking_issues'])} "
                  f"-- not cached, will retry next pass {elapsed:.1f}s")
            with runs_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "chunk": idx,
                    "pages": pages,
                    "input_chars": len(chunk_text_value),
                    "output_chars": len(english),
                    "elapsed_seconds": round(elapsed, 2),
                    "engine": args.ocr_engine,
                    "translator": "qwen3vl-4b-trithemius-q6",
                    "model": args.model,
                    "warn": "output_guard",
                    "output_guard": guard,
                    "retrieval_refs": retrieval_refs,
                    "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                }, ensure_ascii=False) + "\n")
            continue
        out_path.write_text(english.strip() + "\n", encoding="utf-8")
        n_ok += 1
        print(f"  [{idx}/{len(chunks)}] ok pages={pages} "
              f"latin={len(chunk_text_value)} english={len(english)} {elapsed:.1f}s")
        with runs_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "chunk": idx,
                "pages": pages,
                "input_chars": len(chunk_text_value),
                "output_chars": len(english),
                "elapsed_seconds": round(elapsed, 2),
                "engine": args.ocr_engine,
                "translator": "qwen3vl-4b-trithemius-q6",
                "model": args.model,
                "output_guard": guard,
                "retrieval_refs": retrieval_refs,
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            }, ensure_ascii=False) + "\n")

    total = time.time() - t0
    print(f"\n[{args.work}] done: ok={n_ok} skip={n_skip} short={n_short} guard={n_guard} "
          f"retry-short={n_retried} fail={n_fail} "
          f"total={total:.1f}s  out={out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
