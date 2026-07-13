# Errata — prdl-24382

## 2026-06-09 — targeted chunk re-translation (Fable 5 revision pass)

### full_chunk_0001

Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The flagged rendering imported an entire printed-title-page apparatus — an imperial printing privilege, a verse epigram under the name "Richard of Forlì," and the opening of the dedication to Maximilian ("Cattel Bopardiano," "Abbot of Poggiolbelli") — none of which appears anywhere in this chunk's source span. Pages 1–3 are only the BSB digitization cover sheet, the blank leather binding, and the pastedown with shelfmark labels; pages 4–5 (next segment) are manuscript waste leaves, not the title page either.

**Key corrections (verified against the scan):**
- Removed the fabricated/unsupported block (Richard of Forli epigram, imperial privilege, dedication opening): verified by viewing scans of pages 1-5 that no such text exists in or adjacent to this chunk's span
- Imprint on the BSB cover sheet reads 'Oppenheym 1515' in the print, not 'Oppenheim 1515' as the OCR normalized it; rendered with both forms
- Page 2's OCR '[unclear]' is the book's front binding (worn dark leather, no text) - rendered as an editorial line stating absence of text rather than illegibility
- Page 3 (pastedown) content verified and described: pencil shelfmark '4° P. lat. 1239', BSB barcode label '<36610801240012' printed twice over 'Bayer. Staatsbibliothek', and pencil numeral '33'
- Restored the cover sheet's full identifiers visible in the scan: Res/4 P.lat. 1239, urn:nbn:de:bvb:12-bsb00012794-0, VD16 T 1986
- Catalog-form Latin title verified against the scan and translated: 'The Book of Eight Questions of Johannes Trithemius, Abbot of Saint James at Würzburg, though formerly of Sponheim, to Emperor Maximilian'

**Surviving cruxes (flagged in the chunk's translator's note):**
- None. The only Latin in the span is the modern BSB catalog title, fully legible; page 2's '[unclear]' in the OCR corresponds to a textless binding cover, not illegible print.

## 2026-07-10 — removed English AI image-description output from segments 41 and 43 (latin-ocr.txt only)

`latin-ocr.txt` carried raw English vision-model output in two places: segment 41 ("**Page Content:** - Blank white sheet... - A circular hole punch mark...") and segment 43's final line ("The physical condition suggests significant wear at the edges where the paper meets the leather binding..."). The English chunks 0041/0043 are clean charter translations and were not touched. Segment markers retained; segment count and chunk boundaries unchanged.

## 2026-07-10 — collapsed damaged-charter fragment cascades (chunks 41/43 + english.md)

The work's final pages are genuinely damaged Latin charters. The shipped English rendered them as walls of disconnected `[unclear]` fragments ("Through me [unclear]... I judge [unclear]... conspiring [unclear]..."), which read as garbage. Chunk 41 retains its opening (the recoverable charter invocation); the disconnected fragment cascade from "Through me [unclear]" onward is collapsed to an honest damaged-page note. Chunk 43 (entirely `[unclear]` fragments duplicating chunk 41's tail) is replaced with the same honest damaged-page note. The underlying Latin segments 41/43 (English AI wear-description meta) were removed from `latin-ocr.txt` under W1. Segment count and chunk boundaries unchanged.

