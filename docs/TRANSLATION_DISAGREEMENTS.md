# Local translation disagreement review

The first pilot compares two English translations of *In Praise of Scribes*
made from the same BSB printed witness (`bsb00037424`). The queue retains the
original comparison and three dated batches of AI scan assessments. Twenty-three
edits across the two editions include a revision to an earlier pen reading.
Each correction identifies its source folio and the wording it replaced.

The source specification is
`data/translation_disagreements/prdl-24362_de-laude-scriptorum-manualium/review.json`.
It freezes the English, Latin OCR, edition metadata, passage index, and rendered
reading views with SHA-256 digests of UTF-8 text normalized to LF newlines.
It also declares each contextual ledger and correction batch. Missing parts,
changed hashes, and coverage from a different candidate snapshot fail validation.

```console
python scripts/build_translation_disagreements.py
python scripts/validate_translation_disagreements.py
python -m unittest discover -s tests
python scripts/validate_scribes_followup.py
```

The builder writes `index.html`, `queue.json`, `candidates.json`, and four
line-addressable frozen source views under
`review/translation-disagreements/<work-id>/`, outside `site/dist`. The report
can be opened directly or served locally with that report directory as the
server root. The entire repository need not be exposed. No network,
API key, external model, or account is needed to build or validate it.

## Alignment and coverage

The tracks have 21 and 19 translation chunks. Their numbers are not a shared
alignment key. The pilot instead compares token sequences across the specified
English range, using case folding and typographic-apostrophe normalization.
It ignores page/segment marker lines and punctuation-only differences. Every
remaining lexical change is retained with source offsets and context in the
candidate inventory.

Lexical signals about negation, numbers, and longer spans are search aids.
They cannot decide whether a proposition changed: for example, "unwilling"
and "do not wish" trigger a token difference while preserving refusal. The
curated specification records those distinctions explicitly and retains three
excluded controls.

Sixteen selected records receive prioritized triage. All 1,728 lexical changes
also have AI contextual dispositions in three independently authored ledgers,
with 50 detailed findings (including overlaps and shared-error probes). This
does not constitute complete human philological review. Agreement between the
translations can conceal shared errors.

## Priorities and evidence

- **P1:** direct or potentially consequential changes in polarity, modality,
  referent, agency, or beneficiary. Priority is impact, not certainty.
- **P2:** material omissions/recovery candidates and other source problems
  requiring comparison. A fuller alternate OCR is possible evidence for
  recovery, not automatic proof of either translation's correctness.
- **P3:** lower-priority rhetorical ambiguity and paratext identification.
- **Excluded:** retained examples whose lexical differences do not support
  the proposed meaning-changing interpretation.

All assessments remain explicitly attributed to AI. The six original P1 cases
now have direct AI assessments of institutional page images and exact crops,
recorded in `scan-assessments.json`. The seven edits of November 5 are recorded in
`corrections.json`. The November 17 scan assessments and six subsequent edits
are in the `scan-revisions` and `revisions` directories. Folio 6v supports
the command of the prelates and includes Rabanus between Alcuin and Regino.
Folio 13r identifies John as former chancellor of Paris. The dated records
preserve the exact crops, replaced text, and checksums. Human review is pending.

The 23 November batch records ten edits at five loci. The English now names
Peter of Friedberg and dates the printing to 1494, restores the sentence about
finding or buying printed books, specifies sacred books in the feast-day
conclusion, and identifies the inward exercises as the subject of the warning.
The earlier edition also restores the Lord as the subject across folios 9v
and 10r. The three uncertainty markers resolved in these readings retain
their original links in the edition errata.

The original comparison is frozen under snapshots/before-corrections. It is
retained as historical evidence while each affected card shows its local
resolution. Candidate IDs include both English source digests and scope; the
positional-v1 to snapshot-v2 migration map preserves the earlier references.
Five original benchmark seeds remain provisional. The sixth, concerning the
pen on folio 3v, is withheld. The print supports *iterum* and *calamus*. A Latin
reader still needs to adjudicate the possible *intinctus* and its syntax.

Every queued record includes verbatim English and both Latin OCR excerpts,
one-based line numbers, zero-based Unicode character offsets (end exclusive),
and the digest of the source file. Latin page/segment markers are archival
locators, not verified image coordinates. The institutional catalogue is linked
for subsequent scan review.

Earlier English links use an existing passage fragment only when the excerpt
occurs in exactly one indexed passage. Otherwise the link is work-level. T4B
links in the original comparison refer to its frozen work-level target.
The report also records whether an archive quotation survives in the
reading view, avoiding an assumption that raw and edited displays are identical.
Evidence links open the four bundled source views and work offline. Optional
published-reader and institutional-record links open public websites; validation
checks reader targets against the frozen local HTML without fetching live pages.

## Validation limits

The validator independently checks quotations, offsets, line numbers, hashes,
schema, ordering, counts, local links, and fragments. It also regenerates the
outputs in memory and rejects stale artifacts. Tests cover negation, quantities,
omissions, different chunk boundaries, equivalent wording, Unicode references,
ambiguous quotations, source drift, and witness mismatches.

These checks establish artifact integrity. They do not replace a human reading
of the Latin or the source scan, and they do not turn the lexical inventory into
an automatically adjudicated translation.

The correction batches are audited by `validate_scribes_followup.py`, which
replays every recorded change against the preserved before-texts, checks the
edition errata and rendered readings, and verifies the passage and annotation
IDs. `rebuild_scribes.py` targets the Scribes edition. The storehouse phrase
retains an `[ed.]` marker so its annotation ID and later note IDs remain stable;
the work's errata explain that intervention.
