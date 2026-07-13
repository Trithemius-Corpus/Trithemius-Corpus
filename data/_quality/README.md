# Quality Data

## Current release evidence

- `scoreboard_gpt_v3.csv` and `scoreboard_gpt_v3.md` are the public release scoreboard generated from `manifest.json` and per-work metadata.
- `public_release_chunks.jsonl` is the current release chunk ledger. It mirrors the committed `translation_backend=public` rows in each work's `chunks/grades.csv`.
- Each `works/<id>/chunks/grades.csv` keeps the current `public` release rows first. Older pre-release public audit rows are retained with `translation_backend=public-history`.

> **Note on the release-certification rows.** The `translation_backend=public`, `grader=release-certification` rows (one per shipped chunk, 4,353 in total) are **work-level faithfulness/fluency scores stamped per chunk**, not independent per-chunk grades. They are derived from `manifest.json` and `scoreboard_gpt_v3.csv` (`evidence_source` field on each row) and carry a constant adjusted faithfulness within each work. Independent per-chunk grades from the model auditors are the `public-history` rows above them. `hallucinated=false` on all 4,353 certification rows reflects the work-level determination, not a per-chunk check. Treat the per-chunk ledger as a coverage/certification record; for fine-grained quality, read the `public-history` grades and `notes`.

## Historical audit and selection data

- `public_selection_history.jsonl` is historical backend-selection data from earlier public assembly passes. It is not the current release ledger and may contain weak, hallucination-positive, or pre-remediation rows.
- `keep_better_fold.jsonl`, `placeholders.jsonl`, `rerevise_queue.jsonl`, and `style_c_untranslated_gpt_v3.jsonl` are supporting audit/remediation artifacts.
- `gpt55_v3_canonical.summary.json` summarizes the release-level published counts; the detailed current chunk ledger is `public_release_chunks.jsonl`.

Do not recreate `public_selection.jsonl` in this directory for release evidence. Use `public_release_chunks.jsonl` for public validation, and use the history file only for provenance or method reconstruction.
