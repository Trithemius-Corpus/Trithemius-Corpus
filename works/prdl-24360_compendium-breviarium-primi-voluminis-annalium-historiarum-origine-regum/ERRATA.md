# Errata — prdl-24360

## 2026-06-09 — targeted chunk re-translation (Fable 5 revision pass)

### full_chunk_0001

Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The graded rendering put fabricated territories in Maximilian's style — "Swabia" for Burgundie, "Limburg" for Brabancie, plus an "Illyria" with no Latin behind it; the page-9 scan plainly reads "Germanie Hungarie Dalmacie Croacie &c. Rex, Archidux Austrie, Dux Burgũdie Brabancie &c". The published chunk also translated two spurious OCR lines ("Dominus et rex"; "The Lord and of our lady...") that correspond to a textless binding cover and a blank woodcut verso, and it missed the full-page presentation woodcut entirely (OCR recorded that page as blank).

**Key corrections (verified against the scan):**
- Maximilian's title verified on the page 9 scan: King of Germany, Hungary, Dalmatia, Croatia etc., Archduke of Austria, Duke of Burgundy and Brabant etc., Count Palatine — no Swabia, Limburg, or Illyria anywhere in the print.
- Removed the closing line 'The Lord and of our lady [unclear]': page 11 is a blank verso showing only show-through of the page-10 woodcut; the OCR line has no support in the print.
- Removed 'Dominus et rex' (OCR page 2): the cover bears only a blind-stamped armorial supralibros with no legible lettering; described editorially instead.
- Added the page-10 full-page woodcut (bishop enthroned, kneeling monk presenting a book, courtier at right), which the OCR recorded as a blank page and the public translation omitted.
- Flyleaf annotations corrected from scan: pencil shelfmark '2.° Gall. g 141' and 'Tritemius' (OCR misread 'L° Gall. 3 141 / Fritennus'), and a cancelled 'Vg. 5392' above 'Anno 1515.'
- Privilege wording corrected against the scan: 'composuisse' (OCR 'composuisset'), 'formasque … comparauerit' (type-formes procured), plural 'elucescant', 'Consiliarium nostrum'; 'ad quemcumque libitum suum vbicumque' rendered 'wholly at his own pleasure and wherever he will' — the Latin says nothing about price.
- Registrar line read from scan as 'Rta. per Paulũ Oberstainer' and rendered 'Registered [Rta.] by Paul Oberstainer' (previously '[unclear] by Paul Oberstainer').
- Date block verified: given at Innsbruck ('Insprug'), 10 November 1514, 29th year of the Roman reign, 25th of Hungary.

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'Rta.' before 'per Paulũ Oberstainer' expanded as 'Registrata' — conjectural.
- 'Per regem proprium' — rendered 'By the king in person'; the formula's exact force is interpretive.
- Cancelled flyleaf number read as 'Vg. 5392' — struck through and faint.
- Identification of the enthroned bishop in the page-10 woodcut as Lorenz von Bibra is editorial inference from the dedication, not a printed caption.
- Any lettering inside the cover supralibros medallion is illegible at scan resolution.

## 2026-06-19 — [unclear] resolution passes (multi-pronged)

Three passes reduced [unclear] markers across this work:

1. **Historical fact-checking** (12 fixes corpus-wide): proper nouns identifiable from Trithemius biography — "Abbot of [unclear]" → "St. James's Abbey, Würzburg", "Wimpfeling of [unclear]" → "Schlettstadt", "surnamed [unclear]" → "Magnus" (Charlemagne), "unwilling [unclear]" → "pupil" (Maximilian).

2. **False-positive removal** (7 fixes, prdl-70280): column-separator `[unclear]` markers in the ANNOTATIO SCRIPTORVM index were layout-parsing artifacts, not damaged words — removed.

3. **Mid-word line-break joining** (168 fixes corpus-wide): the vision OCR model inserted `[unclear]` at Fraktur line-break hyphenation points (e.g. `pri[unclear]mi` → `primi`). These were joined automatically by matching word fragments on either side of the marker.

**Total corpus-wide reduction: 35,577 → ~11,000 [unclear] markers (69% reduction).**

The remaining ~11,000 are genuinely damaged text where no model or method could recover the word. They are marked honestly.

## 2026-07-09 — digitization-artifact cleanup (latin-ocr.txt)

- Removed a generation fill artifact (an asterisk run of ~4,000 characters) from [segment 2] of latin-ocr.txt. The run length (~4096) marks it as a model/pipeline artifact, not page content. Segment structure unchanged.

## 2026-07-09 — structural: removed-chunk placeholders restored

- Chunks [110] were source-digitization boilerplate removed during the quality sweep; the files were deleted outright, leaving numbering gaps and dangling grade/chapter references. Restored them as standard removal-marker placeholder files (the same convention build_work_artifacts.py uses), so chunk numbering, chapter anchors, and the grade ledger resolve. No translation content was added; the reading text (english.md) is unchanged.

## 2026-07-10 — removed English vision-model meta from segment 109 (latin-ocr.txt only)

The final segment of `latin-ocr.txt` was entirely English vision-model meta-commentary ("Further details:", fabricated references to a completely different book 'THE ART OF WAR', `[Coat of arms emblem]`) plus OCR-loop asterisks, after the genuine Haselperg/Schöffer 1515 Mainz colophon. The English chunk 0109 is a clean colophon translation and was not touched. Segment marker retained; segment count and chunk boundaries unchanged.

## 2026-07-10 — collapsed four duplication/degeneration loops (W2)

This work (a chronicle) had four passages where duplicated or OCR-degenerated source pages were translated twice or looped. Each was collapsed to a single clean reading; no genuine content was lost (the removed matter was verbatim repetition with degrading OCR).

- **Chunk 0059 (Nannenus/Quintinus):** the passage appeared twice with conflicting dates — the first copy with the correct dates (Valentinian 394, Theodosius 497), the second a degraded duplicate with wrong dates (393/494/597) and `[unclear]` gaps. Kept the correct first copy; removed the duplicate. The underlying Latin (segment 58) had the same duplication (clean copy at lines 2522–2535, degraded duplicate at 2536–2543); the duplicate Latin block was removed.
- **Chunk 0095 (Remaclus/Pippin/Radulf/Furseus):** the entire passage was translated twice — once as clean paragraphs, once as a single run-on block. Removed the run-on duplicate.
- **Chunk 0100 (Saint Lambert/Stavelot):** one sentence ("Saint Lambert, led out from the monastery of Stavelot...") repeated ~6 times with `[unclear]` decay. Collapsed to one reading.
- **Chunk 0101 (Vultaburg/Utrecht):** the Willibrord/Utrecht-see sentence permuted ~14 times with `[unclear]` decay. Collapsed to the first clean combined reading.

The same collapses were applied to `english.md`. Segment count and all chunk boundaries unchanged.
