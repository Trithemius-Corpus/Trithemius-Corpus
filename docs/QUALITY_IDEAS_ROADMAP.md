# Quality Ideas Roadmap

Status key: Done = implemented in this working set; Started = partially implemented; Queued = proposed for later work.

| # | Status | Idea |
|---:|---|---|
| 1 | Done | Strict per-chunk release validator for `public` rows. |
| 2 | Done | Compare manifest `chunks_graded` to committed public grade rows per work. |
| 3 | Done | Validate `preamble` and `refusal` flags, not only hallucination. |
| 4 | Done | Validate known wrong-source topical signatures, starting with `historia plantarum`. |
| 5 | Queued | Compare first Latin characters against expected work vocabulary/title anchors. |
| 6 | Done | Add `data/_quality/README.md` explaining current vs historical quality files. |
| 7 | Done | Rename historical `public_selection.jsonl` to `public_selection_history.jsonl`. |
| 8 | Done | Generate `public_release_chunks.jsonl` from committed public release grades. |
| 9 | Done | Make `quality_sweep.py --plan` print the exact data file it is using. |
| 10 | Done | Add `--source working|repo-history` to `quality_sweep.py`. |
| 11 | Queued | Add a single `scripts/release_audit.py` entrypoint for all release checks. |
| 12 | Queued | Add a cross-shell compile check so release checklist commands work in PowerShell and Unix shells. |
| 13 | Queued | Add a Pagefind freshness check comparing index timestamps to generated HTML. |
| 14 | Queued | Add a link checker that validates fragment anchors, not only files. |
| 15 | Queued | Add a generated-file diff summary that hides line-ending churn. |
| 16 | Started | Add a known OCR-artifact registry keyed by work/chunk/signature. |
| 17 | Queued | Add per-work source sanity profiles with expected names, places, incipits, and genre terms. |
| 18 | Queued | Add a topical drift detector for botanical, legal, medical, or astronomical OCR intrusions. |
| 19 | Queued | Add a duplicate-line detector for Latin OCR repeat loops. |
| 20 | Queued | Add a parallel-viewer warning when the Latin source is known OCR-damaged or wrong-source. |
| 21 | Started | Add inline source witness notes for bogus or illegible Latin spans. |
| 22 | Queued | Add a public translation-confidence label that separates machine grade from human certification. |
| 23 | Queued | Add a scoreboard footnote explaining that Tier S is machine-audited, not a critical edition. |
| 24 | Queued | Add a scoreboard filter for chunks with high `[unclear]` density. |
| 25 | Queued | Add a scoreboard filter for works with Style C apparatus. |
| 26 | Queued | Add a scoreboard column for source issues found. |
| 27 | Queued | Add a scoreboard column for first English translation. |
| 28 | Queued | Add a scoreboard column for reading time. |
| 29 | Queued | Add per-work known caveats generated from ERRATA and validator notes. |
| 30 | Started | Add direct links from table-heavy chunks to Style C apparatus pages. |
| 31 | Queued | Add inline apparatus to parallel viewers, not only work pages. |
| 32 | Queued | Add table-specific print CSS for cipher matrices. |
| 33 | Queued | Add a facsimile-first mode for cipher/table chunks. |
| 34 | Queued | Add image thumbnails beside Style C chunk headings. |
| 35 | Queued | Add OCR/source confidence badges on each parallel segment. |
| 36 | Queued | Add a user-facing issue-report link that pre-fills work and chunk id. |
| 37 | Queued | Add a chunk permalink copy button. |
| 38 | Queued | Add previous/next chunk controls inside long work pages. |
| 39 | Queued | Add search facets by genre, work, and apparatus type. |
| 40 | Queued | Add Ctrl/Cmd+K search shortcut. |
| 41 | Queued | Add a recently changed page for reviewers. |
| 42 | Queued | Add release notes generated from git diff and audit results. |
| 43 | Queued | Add a diff-against-previous-public-translation view for revised chunks. |
| 44 | Queued | Add an optional OCR-source/facsimile crop panel. |
| 45 | Queued | Add a public corrections ledger for post-release fixes. |
| 46 | Queued | Add a benchmark set of manually verified chunks for regression testing. |
| 47 | Queued | Add a model-comparison dashboard for GPT, Claude, Fable, MiniMax, and OCR variants. |
| 48 | Queued | Add a fusion-candidate quarantine area outside public corpus pages. |
| 49 | Queued | Add a naming convention for fusion works, review renderings, and canonical translations. |
| 50 | Queued | Add a release gate for review-only terms such as `fusion-patches`, `to seed reviewer`, or private local paths. |
