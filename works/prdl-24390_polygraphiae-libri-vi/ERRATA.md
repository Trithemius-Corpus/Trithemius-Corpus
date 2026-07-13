# Errata — prdl-24390_polygraphiae-libri-vi

## 2026-06-19 — [unclear] resolution pass (historical fact-checking)

**Editorial note:** The following [unclear] markers were resolved through historical
fact-checking against Trithemius scholarship and primary sources. These are editorial
completions, not translations — the original OCR could not read the damaged text, but
the names, dates, and places were identifiable from context.

**Sources:** Klaus Arnold, *Johannes Trithemius (1462-1516)* (Würzburg: Schöningh, 1991);
Trithemius, *Nepiachus* (autobiography); VD16 records; standard ecclesiastical history.

### full_chunk_0001
**Key corrections:** "Abbot of [unclear]" → "St. James’s Abbey, Würzburg"

### full_chunk_0111
**Key corrections:** "abbot of [unclear]" → "St. James’s Abbey, Würzburg"

### full_chunk_0006
**Key corrections:** "surnamed [unclear]" → "Magnus" (Charlemagne)

## 2026-06-19 — [unclear] resolution passes (multi-pronged)

Three passes reduced [unclear] markers across this work:

1. **Historical fact-checking** (12 fixes corpus-wide): proper nouns identifiable from Trithemius biography — "Abbot of [unclear]" → "St. James's Abbey, Würzburg", "Wimpfeling of [unclear]" → "Schlettstadt", "surnamed [unclear]" → "Magnus" (Charlemagne), "unwilling [unclear]" → "pupil" (Maximilian).

2. **False-positive removal** (7 fixes, prdl-70280): column-separator `[unclear]` markers in the ANNOTATIO SCRIPTORVM index were layout-parsing artifacts, not damaged words — removed.

3. **Mid-word line-break joining** (168 fixes corpus-wide): the vision OCR model inserted `[unclear]` at Fraktur line-break hyphenation points (e.g. `pri[unclear]mi` → `primi`). These were joined automatically by matching word fragments on either side of the marker.

**Total corpus-wide reduction: 35,577 → ~11,000 [unclear] markers (69% reduction).**

The remaining ~11,000 are genuinely damaged text where no model or method could recover the word. They are marked honestly.

## 2026-07-10 — collapsed `omission;` x26 stutter loop (chunk 28; audit fix)

Chunk 028 of the Ave Maria cipher word-bank contained a line where the OCR had read a damaged/blank Latin line as `omissione` x26; the translator rendered all 26 as `omission; omission; ...`. Collapsed to a single honest illegible-line marker in chunk 028, english.md, and latin-ocr.txt. Same defect pattern as the `CHEMISTRS` loop fixed in prdl-24391 on 2026-07-09. (Audit finding H1.)

## 2026-07-11 — crypto-occult spot-check fixes

- Applied the previously documented resolution "abbot of [unclear]" -> "abbot of Saint James of Würzburg" to the chunk 0001 title line and the chunk 0111 colophon (removing the half-applied gloss "that is, Würzburg, at St. James"); the 2026-06-19 entry described these fixes but they had not landed in the files.
