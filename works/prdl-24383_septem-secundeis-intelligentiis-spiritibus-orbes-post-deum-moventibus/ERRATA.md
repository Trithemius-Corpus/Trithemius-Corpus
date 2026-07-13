# Errata — prdl-24383_septem-secundeis-intelligentiis-spiritibus-orbes-post-deum-moventibus



## 2026-07-09 — digitization-artifact cleanup (latin-ocr.txt)

- Removed a generation fill artifact (an asterisk run of ~4,000 characters) from [segment 2] of latin-ocr.txt. The run length (~4096) marks it as a model/pipeline artifact, not page content. Segment structure unchanged.

## 2026-07-10 — removed pseudo-Greek hallucination tail from segment 19 (latin-ocr.txt only)

The final segment of `latin-ocr.txt` was ~4 KB of hallucinated pseudo-Greek gibberish (mixed Greek script, fake Latin transliteration, and abbreviation glyphs) plus an English blank-page meta line, after the genuine Nuremberg/Haselperg 1522 colophon (`¶Impressum Nurnberge impens Ioānis Haselbergs, Anno, XXII.`). The English chunk 0019 carries only a brief flagged stutter-summary and does not reproduce the pseudo-Greek. Segment marker retained; segment count and chunk boundaries unchanged. (The segment-2 asterisk wall was already collapsed to a summary note by an earlier fix.)

## 2026-07-10 — removed stutter-summary tail chunk 19 (english + chunk)

Chunk 0019 (88 bytes) was a brief flagged stutter-summary ("And the king, son of [Roli?]... [repeated throughout]") appearing after the genuine Haselperg/Nuremberg 1522 colophon. Replaced `chunks/full_chunk_0019.md` with a removal marker and dropped the line from `english.md`. (The underlying Latin segment 19 — pseudo-Greek hallucination — was removed separately, logged above.) Segment count and chunk boundaries unchanged.
