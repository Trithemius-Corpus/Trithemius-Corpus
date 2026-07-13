# Historical Methodology & Reproducibility - GPT-5.5 Independent Audit

> Status: historical audit note. This records the independent GPT-5.5 audit
> that found the first public quality claim overstated the corpus. It is not
> the current release scoreboard. The current public release view is generated
> from `manifest.json`, `works/*/metadata.json`, and
> `data/_quality/scoreboard_gpt_v3.*`.

## 1. The problem this addresses

The first scoreboard graded each translation with **MiniMax-M2.7 grading
its own (or a sibling backend's) output**, recalibrated to an Opus scale via
a 50-pair sample. It claimed every translated work was A/S tier with
near-zero hallucination.

An independent **GPT-5.5** audit of the *Latin sources* showed this was a
fluency self-grade that did not reliably detect omission or invention. That
audit became the corrective path: keep-better folding, B/C lift sweeps,
re-OCR of weak witnesses, and later hallucination remediation. The final
public release is all-S (S=47 / A=0 / B=0 / C=0 / F=0), but this document
preserves the older audit methodology because it explains why the remediation
was needed.

## 2. Independent grader — `gpt_grade.py`

* GPT‑5.5 via the `codex exec` CLI (ChatGPT plan; no API key), strict
  JSON output schema: `faithful 1‑5`, `fluent 1‑5`, `hallucinated`,
  `preamble`, `refusal`, `notes`, `advice`.
* The grader sees only the Latin source and the English; it is told to
  score independently and to return concrete, applyable revision `advice`.
* `advice` is what makes the grader *also* a revision engine (§3).

## 3. Audit → revise → keep‑better — `gpt_audit_revise.py`

Per translatable chunk of a work:

1. GPT‑5.5 grades the published `public` English.
2. If `faithful ≥ 4` and not hallucinated → finalize as‑is.
3. Else GPT‑5.5 re‑translates from the Latin using its own `advice`,
   re‑grades the revision, and **keeps whichever is better** (higher
   faithful; ties broken toward not‑hallucinated); up to 2 iterations.

Curated OCR placeholders are left untouched. Revised text is isolated to
`translations/gpt-v3/`. A per‑work JSONL ledger
(`_quality/gpt55_v3_<work>.jsonl`) records one row per finalized chunk and
makes every run **resumable with zero rework**.

**Per‑work lock.** `_quality/.locks/<work>.lock`, acquired atomically;
exactly one process per work. Stale‑reclaim only when the lock is old *and*
the work's ledger has been silent > 1500 s. This was added after a pre‑lock
double‑run of `prdl-70287` produced duplicate ledger rows (see §8).

## 4. Sharding & autonomous resume

* `gpt_core_shard.py <S>` runs a shard's work list serially; shards run in
  parallel (work‑lists are disjoint). Codex (ChatGPT plan) caps on total
  volume per rolling window, *not* on concurrency, so parallel shards cost
  the same budget at lower wall‑clock.
* `batch2_watchdog.py` / `mon_watchdog.py` keep shards alive unattended:
  * **liveness = ledger growth**, not the stdout log (the log FD detaches
    across sessions while work continues — an early false‑death source);
  * a shard with no ledger progress for > 900 s is dead → relaunch;
  * **cold‑start grace**: a freshly launched shard with no ledger yet is
    measured from launch time, not treated as instantly dead (this bug
    once spawned a duplicate MON2 — caught before any ledger write);
  * before relaunch, the shard's own **stale locks are cleared** (disjoint
    work‑lists make this safe) so the fresh process can re‑acquire;
  * caps are ridden by retrying every 1800 s until the window frees;
  * the watchdog self‑exits when its shards reach zero remaining.

## 5. Canonicalization — `canonicalize_grades.py` (read‑only)

The append‑only ledgers are never mutated. A derived canonical view holds
exactly one authoritative grade per `(work, record)`:

* 1 row → use it (the normal case);
* > 1 rows (duplicates from pre‑lock / stall‑relaunch) → take the
  **conservative worst** (min faithful; hallucinated if any duplicate flags
  it) and mark the record `ambiguous=true`, so the scoreboard can never
  overclaim on chunks whose on‑disk text is uncertain.

Idempotent; safe to run while shards append.

## 6. Honest scoreboard — `build_scoreboard_gpt_v3.py` (release view)

Two honesty upgrades over the old scoreboard:

1. **Hallucination gate**: `tier = worse(faithful_tier, hall_cap)` —
   S ≥4.0 & ≤5% hall · A ≥3.5 & ≤15% · B ≥3.0 & ≤30% · C ≥2.5 · F <2.5.
   A work that still hallucinates cannot be top‑tier on faithfulness alone.
2. **`U` = Unverified**: works without GPT‑5.5 grades are *not* given the
   old inflated tier; they are explicitly unverified.

It also emits the old(MiniMax) → honest(GPT) **tier migration**. Old
truncated IDs are resolved to full IDs by unique prefix so the contrast is
real. The final public table deliberately reports the GPT-5.5 audit view,
not the original self-grade view.

Companion: `report_quality.py` — per-cluster and per-work quality summaries.

## 7. Folding the gains & honest gaps

* **`fold_keep_better.py`** — replaces a public chunk with the gpt‑v3 text
  only where the GPT‑verified result is genuinely better. Ambiguous chunks
  are folded only if even the *worst* duplicate grade still beats public
  (guaranteed improvement regardless of which duplicate text is on disk).
  Skips work with an active lock (never races a live shard). Takes a one‑time
  reversible local backup of the prior text; idempotent; nothing pushed.
* **`apply_placeholders.py`** — genuinely untranslatable OCR cipher/tabular
  pages with no recoverable prose get a scholarly bracketed
  `[Source illegible …]` note pointing to the source image. This set is
  enumerated in `placeholders.jsonl` and hand-verified rather than heuristic.
  Fixable prose failures are **not** placeholdered, because that would falsely
  claim source damage and discard recoverable content. They remain queued in
  `rerevise_queue.jsonl`, and the step is reversible from a local backup.

## 8. Honest limitations & costs

* **Duplicate‑row cost.** `prdl-70287` (183, pre‑lock) and the batch‑2
  *sermones* `prdl-24393`/`prdl-24394` (~236, from a stall‑relaunch
  incident) were graded twice — wasted codex budget and forced the
  conservative‑worst rule on those chunks. Contained, documented, not
  hidden.
* **Conservative bias is deliberate.** Where the on‑disk text is uncertain
  we under‑claim rather than over‑claim.
* **Large catalogue cost.** The two large bibliographic catalogues
  (`prdl-70289`/`prdl-70290`) dominate the chunk count and are where list-style
  Latin most stresses the grader and translator. The final public table
  carries their completed GPT-5.5 audit results rather than an inherited
  self-grade.
* **Negative results (do not retry).** Sentence‑embedding fuzzy Vulgate
  detection, the v3 Latin→English glossary sweep, and the full parallel
  retrieval index were each built and measured **ineffective** for this
  OCR/register profile — the binding constraint is source OCR damage, not
  retrieval. GPT‑5.5 reading damaged OCR and marking `[unclear]` is the
  only lever that works.

## 9. Reproduction (in order)

```bash
# 1. audit a work / shard (resumable, isolated)
python scripts/gpt_core_shard.py <SHARD>          # + watchdog for unattended
# 2. canonicalize (read-only, idempotent)
python scripts/canonicalize_grades.py
# 3. honest scoreboard + quality report
python scripts/build_scoreboard_gpt_v3.py
python scripts/report_quality.py
# 4. fold gains into local corpus (reversible, idempotent, no push)
python scripts/fold_keep_better.py --apply
# 5. honest placeholders + re-revise queue (reversible, no push)
python scripts/apply_placeholders.py --apply
```

Outputs land in `data/corpus/_quality/` (`gpt55_v3_*.jsonl`,
`gpt55_v3_canonical.jsonl`, `scoreboard_gpt_v3.{md,csv}`,
`keep_better_fold.jsonl`, `placeholders.jsonl`, `rerevise_queue.jsonl`) and
in per‑work `translations/gpt-v3/`, with a reversible local backup taken for
each fold/placeholder step. **No step in this pipeline pushes; publication is a
separate, gated decision.**
