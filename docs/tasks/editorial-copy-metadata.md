# Editorial copy and metadata correction

Scope: local corrections and validation; no deployment or remote writes.
Baseline: `0e38a37671a5e3b5decd11c19fe82de79883cae7`.

Acceptance criteria:

- The homepage and footer agree with LICENSE: generated translations/data are
  CC0; documentation/code/arrangement are CC BY 4.0. Translation Book metadata
  also identifies CC0.
- T4B links describe the prepared view without a grade-based recommendation.
- Introductions remain complete after obsolete grade claims are removed from
  their source prose. Rendering no longer deletes clauses.
- Scribes uses 1492 for composition and 1494 for the printed witness in both
  tracks and the manifest. Evidence: the stored BSB provider manifest title
  records the 1492 dedicatory letter; its Creation field dates the print to 1494.
- Only explicit `composition_year` metadata is labeled Composed or emitted as
  Book `dateCreated`. Legacy work dates are labeled cautiously; `source_year`
  identifies the edition. Other composition dates were not researched here.
- Translation-priority statements reflect the bibliography survey's limits,
  including incomplete coverage for Hucbald, and link to the survey.
- Translation bodies, cipher apparatus, source transcriptions, audit records,
  and passage identities remain unchanged.

The public checkout lacks the private Style C build inputs. Use the bounded
editorial refresh, which calls the existing renderers and replaces only named
editorial sections of the committed publication. This avoids losing cipher
apparatus during a full rebuild. Normal future builds use the corrected
templates and introductions.

Local validation sequence:

```console
python scripts/refresh_editorial_pages.py
python scripts/build_publication_exports.py
npx --yes pagefind@1.5.2 --site site/dist
python scripts/validate_editorial_copy.py
python scripts/validate_release.py
python scripts/validate_reader.py
python scripts/validate_passages.py
python scripts/validate_publication_exports.py
```

Before editing, the release and reader validators passed. Existing warnings:
the unpublished Zenodo DOI placeholder and an older Pagefind index.

Completed validation:

- Editorial copy: 73 existing introductions match their sources; qualified
  survey claims, rights summaries, and date metadata pass.
- Release validator: passed for 47 translatable witnesses, 4 skipped records,
  and 4,400 chunks. The existing unminted Zenodo DOI placeholder is its only
  remaining warning; the search freshness warning is resolved.
- Reader validator: passed across 166 pages and 5 representative fixtures.
- Passage validator: passed for 45,875 passages, 10,167 annotations, and
  3 TEI pilots.
- Publication exporter rebuilt 47 EPUB and print editions; their structural
  validator passed. Official EPUBCheck was not run for this copy-only update.
- Search rebuilt with the existing Pagefind version, 1.5.2, indexing 166 pages.
  The local browser returned 63 results for the new phrase "project survey".
- In-app browser checks confirmed the homepage rights and survey link, Scribes
  dates and complete introduction, and the Vindex edition date. Narrow-screen
  checks showed no horizontal overflow at a 390px viewport override.
- All 74 standard/T4B work pages match the baseline outside the allowed
  editorial sections and footers, after newline normalization. Translation sources, audit records,
  passage indexes, TEI, and IIIF artifacts are unchanged.
- Python compilation and `git diff --check` passed.

Changes remain local on `fix/editorial-copy-metadata`; nothing was pushed or
deployed. This corrects the reviewed presentation and metadata issues, not the
underlying translation disagreements or every historical date in the corpus.
