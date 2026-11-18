# Local translation disagreement review

The first pilot compares two English translations of *In Praise of Scribes*
made from the same BSB printed witness (`bsb00037424`). The queue retains the
original comparison, the six AI scan assessments, and the seven resulting
local edits. Each corrected passage links back to its source evidence.

The source specification is
`data/translation_disagreements/prdl-24362_de-laude-scriptorum-manualium/review.json`.
It freezes the English, Latin OCR, edition metadata, passage index, and rendered
reading views with SHA-256 digests of UTF-8 text normalized to LF newlines.
Changing a frozen input causes the build to fail until the evidence is reviewed
and the specification is deliberately updated.

```console
python scripts/build_translation_disagreements.py
python scripts/validate_translation_disagreements.py
python -m unittest discover -s tests -p test_translation_disagreements.py
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
recorded in scan-assessments.json. Seven local translation edits are recorded
in corrections.json, with original texts, hashes, normalized Latin, and errata.
Human review remains undocumented; the legacy facsimile_verified flag remains
false and is not used to represent the separate AI image-assessment layer.

The original comparison is frozen under snapshots/before-corrections. It is
retained as historical evidence while each affected card shows its local
resolution. Candidate IDs include both English source digests and scope; the
positional-v1 to snapshot-v2 migration map preserves the earlier references.
The six benchmark fixtures are AI scan-assessed seeds, not human-validated gold.

Every queued record includes verbatim English and both Latin OCR excerpts,
one-based line numbers, zero-based Unicode character offsets (end exclusive),
and the digest of the source file. Latin page/segment markers are archival
locators, not verified image coordinates. The institutional catalogue is linked
for subsequent scan review.

Earlier English links use an existing passage fragment only when the excerpt
occurs in exactly one indexed passage. Otherwise the link is work-level. T4B
links are work-level because this reading view lacks equivalent passage
anchors. The report also records whether an archive quotation survives in the
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

The first correction batch is audited by `validate_scribes_followup.py`, which
replays every recorded change against the preserved before-texts and checks the
passage/annotation IDs. `rebuild_scribes.py` rebuilds only this work, avoiding
unavailable private cipher-layout inputs. The no-longer-unclear storehouse phrase
retains an `[ed.]` marker so its annotation ID and later note IDs remain stable;
the work's errata explain that intervention.
