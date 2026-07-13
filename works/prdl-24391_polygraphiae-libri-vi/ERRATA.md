# Errata — prdl-24391_polygraphiae-libri-vi

## 2026-06-19 — [unclear] resolution pass (historical fact-checking)

**Editorial note:** The following [unclear] markers were resolved through historical
fact-checking against Trithemius scholarship and primary sources. These are editorial
completions, not translations — the original OCR could not read the damaged text, but
the names, dates, and places were identifiable from context.

**Sources:** Klaus Arnold, *Johannes Trithemius (1462-1516)* (Würzburg: Schöningh, 1991);
Trithemius, *Nepiachus* (autobiography); VD16 records; standard ecclesiastical history.

### full_chunk_0014
**Key corrections:** "Abbot of [unclear]" → "St. James’s Abbey, Würzburg"

### full_chunk_0004
**Key corrections:** "Wimpfeling of [unclear]" → "Schlettstadt"

### full_chunk_0006
**Key corrections:** "surnamed [unclear]" → "Magnus"

## 2026-07-09 — digitization-artifact cleanup (latin-ocr.txt)

- Removed a vision-model hallucination loop (the token 'CHEMISTRS' and spelling variants repeated 295 times) from [segment 120] of latin-ocr.txt. The source page is illegible in the scan (the paired English chunk already carries the illegible-page marker); the loop was model babble, not page text.

## 2026-07-10 — removed post-FINIS duplicate (chunk 136; audit fix)

Segment 136 reprinted the closing prophecy material after the genuine FINIS (chunk 0135: 'Laus Deo omnipotenti. FINIS.' / '*END.*'). Replaced chunk 0136 with a removal marker and truncated english.md at '*END.*'. (Audit finding M1.)

## 2026-07-11 — crypto-occult spot-check fixes

- Swept two straggler OCR variant tokens ("CHEMICS", "CHEMIES") that survived immediately before the 2026-07-09 CHEMISTRS-loop removal note in latin-ocr.txt segment 120.
