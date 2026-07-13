# Errata — prdl-32286

## 2026-06-09 — targeted chunk re-translation (Fable 5 revision pass)

### full_chunk_0001

Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The public version rendered the title-page imprint date as 1533, but the print clearly reads "Anno M.D.XXXIIII" (1534) — an OCR stroke-drop, hence the 1533/1534 discrepancy with the catalog. In the preface heading on page 8 it called Trithemius "Abbot of Sponheim," but the print reads "Abbatis Peapolitani" (Abbot of Peapolis, i.e. St James's, Würzburg) — translated content not present in the source. It also silently absorbed segment 2's text to finish the final sentence, which actually breaks mid-word at the chunk boundary.

**Key corrections (verified against the scan):**
- Title-page date corrected to M.D.XXXIIII [1534]; the imprint line shows four minims after XXX
- Preface heading corrected to 'Abbot of Peapolis' per print 'Abbatis Pea-politani' on page 8; old 'Abbot of Sponheim' was unsupported there
- 'by the holy angels' (a sanctis angelis) restored on page 10; OCR 'letis' / old 'blessed angels' not what the print reads
- 'Medium ... iter disputationis' rendered as 'a middle path of the disputation' (old version dropped 'middle'); 'sacer ... Gregorius' rendered 'holy Gregory'
- Chunk-final sentence now ends at the printed break 'promissae co—' with catchword 'gnitio' noted, instead of absorbing segment 2's continuation
- Handwritten title-page ex-libris read from scan as 'Conuentus Monacensis Carmelitarum Discalceator(um)'; library marks (Carmelite bookplate p.3, barcode p.4, BIBLIOTHECA REGIA MONACENSIS stamp p.7) rendered as bracketed editorial lines
- Flyleaf pencil notes (p.5) rendered as partly legible with conjectural readings instead of confident text

**Surviving cruxes (flagged in the chunk's translator's note):**
- Flyleaf pencil annotations on page 5 only partly legible; 'Philos.', 'Trithem', and 'saec. XV 1482' are conjectural readings
- Ex-libris expansion 'Discalceator(um)' is conjectural (final letters abbreviated/cramped in the scan)
- Chunk ends mid-word at page 10's catchword 'gnitio'; sentence concludes in the next chunk
