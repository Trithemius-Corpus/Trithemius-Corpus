# Scribes follow-up implementation

Authorized 2026-11-05: execute the five reviewed steps in order, locally.
The follow-up builds on the copy and metadata changes and the initial queue.
Work was authorized locally. AI scan assessment must not be called human
review. Supported local corrections receive an explicit evidence/errata record;
unresolved readings remain marked.

1. [x] Queue identity, permalinks, schema, independent invariants, snapshot IDs, CI.
2. [x] Survey classifications, rights link, triage summaries, boundary case.
3. [x] Source-image evidence and decisions for all six P1 cases.
4. [x] Contextual review of remaining inventory, with visible dispositions and
   checks for shared errors.
5. [x] Small supported correction batches, errata, preserved links, refreshed
   queue/exports, and initial benchmark fixtures.

Each stage records its validation before the next begins. No claims of a
complete human-reviewed edition are made by this work.

Stages 1–2: 17 regression tests and queue/editorial validators passed. The 1,728
original candidate IDs have a snapshot-v2 migration map; token spans did not
change. The survey records 34 witnesses with no prior English located, 7 with
partial translations, 2 complete, and 4 unresolved. These counts include
the already documented excerpts of the *Eight Questions*. The catalogue
filter for no complete prior English covers 23 texts across 41 witnesses.

Stage 3: directly inspected BSB canvases 5, 8, 20, 32, and 40 and six exact
crops. Recorded image hashes, rights, folio labels, normalized Latin, reasoning,
and AI review identity in scan-assessments.json. The six cases support local
correction proposals; no human verification is claimed. The OCR marker offset
of +1 relative to IIIF canvas numbers was checked against the text itself.

Stage 4: three independent AI reviewers covered all 1,728 snapshot-v2 candidates
in 106 contextual groups. Exact one-to-one coverage and their source quotations
were independently validated on integration. Dispositions: 1,579 no material
change found, 76 need source review, 55 overlap existing cases, 10 layout
furniture, 8 alignment uncertainties. Fifty detailed findings include overlaps
and shared-error probes, not fifty established new errors. The complete ledgers
and a consolidated readable report are retained. Only the six scan-assessed
cases are accepted for the first local correction batch.

Stage 5: seven exact English corrections were applied across eight assembled
text/chunk files (three earlier-track changes and four T4B changes). Original
inputs are frozen under snapshots/before-corrections. Corrections are replayable
from proposed-corrections.json and audited by corrections.json. Both ERRATA
files identify the AI method, original/revised wording, Latin, source image,
and reasoning. Machine-audit labels now explicitly predate the corrections.

The six resolved prioritized records retain their original comparison and show
the local resolution plus scan evidence. A separate current-text recomparison
is generated without carrying old contextual classifications onto new IDs.
The November 5 batch originally supplied six provisional benchmark seeds.
Its source evidence remains available alongside the subsequent revision.

Completed local checks:

- 19 regression tests, including truncated witness IDs, independent invalid
  metadata, coverage conservation, sentence reordering/EOF insertions, and
  initial/hashchange navigation to excluded records.
- Queue schema, all 70 curated quotations, snapshots, source/image/crop hashes,
  exact crop pixels, local links, contextual coverage, and deterministic output.
- Correction replay: only the seven recorded semantic edits plus the explicit
  historical-audit header clarification; 99 passage and 27 annotation IDs retained.
- Editorial copy; reader (166 pages); passages (45,875); annotations (10,167);
  three TEI pilots; IIIF (3 manifests, 753 canvases); Study reader; and structural
  validation of 47 EPUB/print exports.
- Pagefind 1.5.2 rebuilt the local 166-page index.
- Release validator passed with only the existing unminted Zenodo DOI warning.
- Browser content/state checks confirmed excluded permalink revelation, the
  applied-correction panel and scan image, revised Scribes wording at the old
  passage fragment, and honest AI/historical-audit labels. Browser screenshot
  capture was unavailable in this session; no new UI screenshot is claimed.
- `git diff --check` passed. Evidence files are not excluded by gitignore.

On 2026-11-17, the official pinned EPUBCheck 5.3.0 validated all 47 EPUBs
locally using Java 17, with zero warnings or errors.

## November 17 scan revisions

The second batch records six edits across the two editions. Folio 6v supports
the command of the prelates and includes Rabanus in the list of monastic writers.
Folio 13r identifies John as former chancellor of Paris. Both English editions
now mark the possible modifier “dipped” on folio 3v as uncertain. Its benchmark
seed is withheld pending adjudication by a Latin reader. The other five original
seeds remain provisional. The frozen contextual judgments cover 1,728 candidates
and the consolidated report now attaches the later scan decisions to their
three original findings, including the shared omission of Rabanus.

## November 23 scan revisions

The third batch records ten edits at five loci across the two English editions. The colophon now names Peter of Friedberg as the Mainz printer and dates the printing to 1494. The dedication retains 1492. The other four findings concern buying printed books, sacred books on feast days, the monk’s inward exercises, and the Lord as subject across folios 9v–10r. Three former uncertainty links in the standard edition now lead to their dated errata. The separate pen modifier still awaits a Latin reader. [Scan assessments](../../data/translation_disagreements/prdl-24362_de-laude-scriptorum-manualium/scan-revisions/2026-11-23.json) · [Disagreement queue guide](../TRANSLATION_DISAGREEMENTS.md)
