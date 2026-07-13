# Errata — prdl-24357

## 2026-06-09 — targeted chunk re-translation (Fable 5 revision pass)

### full_chunk_0038

Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The public version smoothed real readings rather than leaving gaps: it rendered "pensionem eis assignando" as "assigning persons to them" (the print plainly reads a pension for monks sent to the studia generalia), mistranslated the Art. 16 rubric "De magistro noviciorum" as "governance of novices," and dropped half of the Art. 18 rubric ("Ne bona monasteriorum partiantur" — that the goods be NOT divided) plus "et abbatis similiter." It also silently absorbed the mid-word chunk boundaries (ordi-/nantes at the start, appellati-/one at the end) and omitted the printed folio number XXXIX.

**Key corrections (verified against the scan):**
- Page mapping corrected: the chunk is on scan pages 82-83 (printed fol. XXXIX), not 83-84; page 84 (fol. XL) begins segment 39 — verified by matching first/last lines.
- Art. 16: print reads 'pēsionē eis assignādo' = pensionem eis assignando, 'assigning them a pension' — not 'assigning persons to them' as previously published; also 'cōpetēter' (in fitting manner) restored and 'bn̄dicti.xij.' confirmed against OCR's 'xi.'
- Art. 16 rubric: print reads 'De mḡro nouicioz̄' = De magistro noviciorum, 'Concerning the master of the novices' — not 'governance of novices.'
- Art. 18 rubric: print reads 'Ne bona monasterioz̄ partianf ſed oibus in cōmuni puideaf' — the prohibition clause 'be not divided up' was missing from the public heading.
- Art. 18 end: print reads 'vsq̄z ad puētus quorūcūq̄z officiarioz̄ z abbatis sifr' — 'and of the abbot likewise' (similiter) restored; OCR had garbled this to 'sit.'
- Art. 17: print reads 'q̄ dr̄ corruptela' (quae dicitur corruptela, 'which is called a corruption') and passive 'tn̄ et alij ob h̄ nō excludunf' ('others are not on this account excluded').
- Folio number XXXIX restored as an editorial line; the faint XXXIX-shape atop page 83 verified as mirror show-through, not print.
- Both mid-word chunk boundaries now marked explicitly instead of silently completed ('ordi-nantes' opening; 'quacumque appellati-' closing, completed '-one semota' in the next chunk).

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'de sta. mo.' — the print's abbreviated title citation for Periculoso; expansion (de statu monachorum/monialium; officially De statu regularium) uncertain, translated as 'on the state of monastics' with the abbreviation shown.
- 'mādat̄' (p. 82, line 3) expanded as 'mandatur' ('is commanded to be observed'); 'mandamus' cannot be fully excluded.
- 'ſeo' in the Art. 18 rubric read as 'sed' (worn/broken d; OCR transcribed 'leo') — flagged as conjectural.
- 'fiat resolutio' (Art. 18) rendered literally as 'let an undoing be made'; the prior 'reduction' was a gloss.
- Art. 18 cites Rule 'ca.33' in the print though the matter (distribution per need) is Rule ch. 34 — translated as printed and flagged.
- Art. 22's compressed citation string 'sup h̄ eodē ti. cō. dn̄i bn̄i. pape. xij.' — parse of the abbreviation cluster ('on this same title, the constitution of...') partly conjectural.

## 2026-07-10 — removed fabricated pseudo-Greek paragraph from segment 93 (latin-ocr.txt only)

A single fabricated pseudo-Greek paragraph was inserted into `latin-ocr.txt` between the genuine 1493 Stuchs/Sulzbach colophon and the `BIBLIOTHECA REGIA MONACENSIS` stamp; it name-drops Pericles and uses the word 'φαντασμαγορικῷ', coined c. 1800 — an obvious OCR-model hallucination. Removed that one line. The English chunk 0092 (this work's numbering is offset by one) is a clean colophon translation and was not touched. Segment count and all chunk boundaries unchanged.

## 2026-07-10 — removed OCR-stutter name-list tail (chunk 94 + english.md tail)

After the genuine 1493 colophon and the name-list of rents, the shipped text degenerated into a long OCR-stutter loop — the entries "Lady Petronia de Castro / Lady Johanna de Castro" (and `[unclear] Johanna de Caiett/Caittin/Cayett/..." variants) repeating dozens of times, ending in orphan fragments ("for himself / And / and if"). Replaced `chunks/full_chunk_0094.md` (the orphan-fragment chunk) with a removal marker and truncated the `english.md` tail at the genuine deduplicated name list ("Lady Johanna de Castro."). The fabricated pseudo-Greek paragraph in segment 93 was removed separately (logged above). Segment count and chunk boundaries unchanged.

## 2026-07-10 — removed duplicated visitation block (chunk 14 + english.md)

A half-page block ("Greater diligence must be applied in inquiring about abbots and their manner of life...") appeared twice within chunk 14. Removed the duplicate copy from both the chunk and `english.md`.

## 2026-07-10 — documented chunk/segment off-by-one (known limitation, back half)

This work has 94 English chunks against 95 Latin segments: chunk 52's English covers Latin segments 52 *and* 53 (the statute on visitors' mounts and the rubric "Concerning the appointment of the presidents" were merged into one translation chunk), shifting every subsequent chunk by one against the Latin. As a result the side-by-side parallel viewer shows the wrong Latin next to the English for the back half of the work (chunks 53–94 align with Latin segments 54–95, and segment 53 has no dedicated English chunk).

The reading text (`english.md`) is complete and correct — no content is missing, only the per-segment alignment is offset. A proper fix requires splitting chunk 52 at the "Concerning the appointment of the presidents" rubric and renumbering chunks 53–94 → 54–95 (43 file renames + grades/metadata rebuild); deferred to v1.1 to avoid destabilizing the parallel viewer two days before release. (The chunk/segment counts: 94 chunks / 95 segments; the grades ledger's per-chunk rows are likewise offset by one in the shifted range — see the grades note.)
