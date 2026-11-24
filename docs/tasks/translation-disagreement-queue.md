# Translation disagreement queue: In Praise of Scribes

Historical log of the initial queue. The 2026-11-05 implementation, scan review,
contextual coverage, and local corrections are recorded in `scribes-followup.md`.

Scope: compare the earlier and Trithemius 4B English tracks for the BSB
`bsb00037424` printed witness; build and validate a local editorial review queue.
No translation edits, source repairs, deployment, publication, or API inference.
The previous copy/metadata changes remain in the same local working tree.

Acceptance criteria:

- Compare corresponding text rather than equating the 21 earlier chunks with
  the 19 T4B chunks.
- Put disagreements affecting propositions, referents, negation, quantities,
  or material omissions ahead of wording preferences.
- Preserve verbatim quotations, source hashes, exact character/line locations,
  both Latin OCR witnesses, and the limits of source-image mapping.
- Record AI triage as provisional. No item is called human-reviewed or
  facsimile-verified; neither English track automatically wins.
- Keep a reproducible lexical-difference inventory and explicit exclusions
  alongside the curated queue. Lexical coverage is not semantic completeness.
- Provide a readable, filterable local report and machine-readable records
  outside `site/dist` and its search index.
- Validate source identity, citations, stale inputs, schema, ordering, output
  determinism, meaningful test cases, and the local review interface.

Status: implemented and locally validated.

Delivered:

- Fifteen provisional review items: 6 P1, 7 P2, and 2 P3; three excluded
  equivalent-wording controls are retained separately.
- A complete scoped token-difference inventory of 1,728 lexical changes.
  This is not an assertion that all semantic disagreements have been found.
- Sixty-six exact English/Latin quotations with source digests and offsets;
  all queued English excerpts are present in the frozen reading views.
- A filterable HTML report, queue JSON, lexical inventory, and four local
  source views with line anchors under `review/translation-disagreements/`.
- An offline builder, validator, JSON schema, and 12 focused regression tests.

Validation completed:

```console
python scripts/build_translation_disagreements.py
python scripts/validate_translation_disagreements.py
python -m unittest discover -s tests -p test_translation_disagreements.py -v
python -m py_compile scripts/build_translation_disagreements.py scripts/validate_translation_disagreements.py tests/test_translation_disagreements.py
```

All checks passed. Generated inline JavaScript also passed `node --check`.
The validator regenerates the report in memory and compares every output,
including source views, to establish deterministic freshness. It independently
checks the 66 quotations, line/character references, schema, counts, priority
order, local links, and reader fragments. Frozen-input mismatches fail closed.

In-app browser checks confirmed P1 filtering (6 records), P2 + Aristotle search
(1 record), excluded controls (3 records), Latin evidence expansion, and a
working source link to T4B English line 135. At a 390px viewport override, the
375px content viewport and document width matched; text columns stacked and
no horizontal overflow appeared. The temporary viewport override was reset.

Automatic approval review rejected a server rooted at the whole repository.
The preview instead serves only the report directory, with four bundled
evidence views. No repository-root server was started. Optional published-reader
and catalogue links were validated against local references, without live
source requests.

The existing translation files, source metadata, public site, search index,
and prior copy corrections were not edited by this task. No deployment,
remote write, external inference, or translation correction occurred. Every
triage item remains pending human/source-image adjudication.
