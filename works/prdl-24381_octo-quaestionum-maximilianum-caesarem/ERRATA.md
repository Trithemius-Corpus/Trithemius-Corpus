# Errata — prdl-24381_octo-quaestionum-maximilianum-caesarem

## 2026-06-19 — [unclear] resolution pass (historical fact-checking)

**Editorial note:** The following [unclear] markers were resolved through historical
fact-checking against Trithemius scholarship and primary sources. These are editorial
completions, not translations — the original OCR could not read the damaged text, but
the names, dates, and places were identifiable from context.

**Sources:** Klaus Arnold, *Johannes Trithemius (1462-1516)* (Würzburg: Schöningh, 1991);
Trithemius, *Nepiachus* (autobiography); VD16 records; standard ecclesiastical history.

### full_chunk_0003
**Key corrections:** "abbot of [unclear]" → "St. James’s Abbey, Würzburg" (Trithemius’s abbacy from 1506)

## 2026-07-09 — structural: removed-chunk placeholders restored

- Chunks [40] were source-digitization boilerplate removed during the quality sweep; the files were deleted outright, leaving numbering gaps and dangling grade/chapter references. Restored them as standard removal-marker placeholder files (the same convention build_work_artifacts.py uses), so chunk numbering, chapter anchors, and the grade ledger resolve. No translation content was added; the reading text (english.md) is unchanged.

## 2026-07-10 — removed OCR-stutter tail chunk 39 (english + chunk)

The final chunk (0039) was a literal English rendering of an OCR stutter — Latin segment 39 read `Dominus et dominicae / et dominicae / et dominicae ...`, shipped as "The Lord and Sundays / and Sundays". The work closes at chunk 38's honest illegible-pages note. Replaced `chunks/full_chunk_0039.md` with a removal marker and dropped the trailing stutter from `english.md`. Segment count and chunk boundaries unchanged.
