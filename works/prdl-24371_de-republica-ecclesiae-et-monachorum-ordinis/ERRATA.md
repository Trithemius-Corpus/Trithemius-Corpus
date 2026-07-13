# Errata — prdl-24371_de-republica-ecclesiae-et-monachorum-ordinis

## 2026-07-10 — removed modern calibration ruler from segment 11 (chunk 11)

Segment 11 (the final segment of `latin-ocr.txt`) contained the right-edge line-slivers of the last printed page followed by OCR of a modern photographic color-calibration ruler, including the anachronistic copyright string `© 2007 digitalfoto-trainer.de`. The sermon concludes at chunk 10 with its doxology ("...who lives and reigns without end. Amen.").

- `latin-ocr.txt` segment 11: truncated to drop the ruler and its `mm`/copyright tail (lines 438–581). The fragmentary genuine Latin slivers above it are retained as an honest damaged-page record.
- `chunks/full_chunk_0011.md`: replaced with a removal marker. The shipped English of chunk 11 was a wall of `[unclear]` tokens translating those slivers; it carried no recoverable content beyond what chunk 10 already closes.
- `english.md`: trailing junk paragraph removed (the work now ends at "...without end. Amen.").
- `chunks/grades.csv`: chunk 11 note updated to record the removal.
