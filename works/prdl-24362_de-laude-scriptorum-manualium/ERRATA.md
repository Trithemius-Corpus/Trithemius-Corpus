# Errata — prdl-24362_de-laude-scriptorum-manualium

## 2026-06-19 — [unclear] resolution passes (multi-pronged)

Three passes reduced [unclear] markers across this work:

1. **Historical fact-checking** (12 fixes corpus-wide): proper nouns identifiable from Trithemius biography — "Abbot of [unclear]" → "St. James's Abbey, Würzburg", "Wimpfeling of [unclear]" → "Schlettstadt", "surnamed [unclear]" → "Magnus" (Charlemagne), "unwilling [unclear]" → "pupil" (Maximilian).

2. **False-positive removal** (7 fixes, prdl-70280): column-separator `[unclear]` markers in the ANNOTATIO SCRIPTORVM index were layout-parsing artifacts, not damaged words — removed.

3. **Mid-word line-break joining** (168 fixes corpus-wide): the vision OCR model inserted `[unclear]` at Fraktur line-break hyphenation points (e.g. `pri[unclear]mi` → `primi`). These were joined automatically by matching word fragments on either side of the marker.

**Total corpus-wide reduction: 35,577 → ~11,000 [unclear] markers (69% reduction).**

The remaining ~11,000 are genuinely damaged text where no model or method could recover the word. They are marked honestly.

## 2026-07-10 — removed modern calibration ruler from segment 21 (latin-ocr.txt only)

The final segment of `latin-ocr.txt` ended with OCR of a modern photographic color-calibration ruler, including the anachronistic copyright string `© 2007 digitalfoto-trainer.de`, after the genuine colophon (`Desideratus finis...Anno virginei partus.M.cccc.xciij.` / `Monasterij Chypensis.`) and the library stamp (`BIBLIOTECA REGIA / UNIVERSITATIS MONACENSIS`). The ruler was never translated (the English closes at chunk 0021 with the genuine colophon), so no English chunk was changed. Removed the ruler block from the tail of segment 21 only; segment count and all chunk boundaries unchanged.
