# Errata — prdl-70292

## 2026-06-09 — targeted chunk re-translation (Fable 5 revision pass)

### full_chunk_0001

Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control. The audit row for this chunk in `chunks/grades.csv` describes the superseded text.

**What was wrong:** The old translation presented Trithemius as the work's author, though the title page reads "È IOA. TRITHEMII manuscripto eruta" (unearthed FROM a manuscript of Trithemius); it dropped the sixth authority Thetel and misassigned the nations (it called Chael an Egyptian and Hermes a Persian, where the print brackets Raphael and Chael together as Jews, makes Hermes the Egyptian, and Thetel the Persian). It also fabricated lines from C. G. Jung's bookplate — "Ravis, do not be silent," "God, when called, will be present" (twice), "T. G. Jurg" — in place of the actual motto "vocatus atque non vocatus deus aderit." The sigil descriptions themselves were mostly supported, with smaller slips.

**Key corrections (verified against the scan):**
- Removed the standalone 'Johannes Trithemius' author byline; the e-rara cover sheet's 'Trithemius, Johannes' is now bracketed as the library's catalogue attribution, and the title-page line rendered 'Unearthed from a manuscript of Johannes Trithemius' (print: 'È IOA. TRITHEMII manuscripto eruta', verified at zoom of page 10).
- Restored the sixth authority THETELE ('Thetel, a Persian'), omitted by the OCR and the public translation (verified in the title-page author block, page 10).
- Corrected the brace pairing of authors: Raphael and Chael share 'Iudæis' (Jews); Hermes is 'Ægyptio' (an Egyptian); Thetel is 'Persa' (a Persian). The public version had 'Chaele, an Egyptian' and 'Hermes, a Persian'.
- Page 3 identified as C. G. Jung's bookplate: winged figure, shield, blackletter 'C. G. Jung', vertical motto 'vocatus atque non vocatus deus aderit' ('Called or not called, God will be present') — replacing the fabricated 'Ravis, do not be silent / T. G. Jurg' lines.
- Page 5 pencil annotations read from the scan: 'Rogers / Budge' (uncertain), an abbreviation perhaps 's. n. e. l.' above a boxed English 'no place, or name', and a code perhaps '52/48' — replacing the bare 'No place or name'.
- Print readings confirmed against pages 12-14 where OCR was damaged: 'scias' (know), 'aduersisque casibus' (adverse mishaps), 'solius est Dei', 'omnique molestia', 'si quis secum portauerit', 'sanum' for OCR 'fanum'.
- 'Tauri imago... ad maleficia iuuare dicitur' rendered 'is said to help toward deeds of sorcery' — the print has no contrary preposition; the public 'against sorceries' was unsupported.
- Lion/Sagittarius entry: print really reads 'si in lapide sit' with no stone named; noted editorially instead of smoothing.
- Segment ends mid-sentence at the page-14 catchword ('redde-'); marked as a chunk-boundary break instead of the public version's '[unclear]', without absorbing segment 2's text.

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'arca & sagitta' — print reads arca ('chest'), evidently a misprint for arcu ('bow'); translated 'bow' with bracketed note.
- 'inter myrthi arboris' — elliptical Latin ('amid a myrtle tree'); translated as printed and flagged.
- 'ad maleficia iuuare' — grammatically 'help toward sorceries', not 'against'; flagged in the note.
- 'loqui cohibere' in the hoopoe entry — 'restrain their speech' (the print's reading; cognate lapidaries have 'compel to speak').
- Ink note on the pastedown: 'Rariss. liber' ('a most rare book') — conjectural, partly obscured by marbling.
- Pencil annotations on the flyleaf: 'Rogers / Budge', 's. n. e. l.', '52/48' — all conjectural readings.

## 2026-07-09 — digitization-artifact cleanup (latin-ocr.txt)

- Replaced the body of [segment 20] of latin-ocr.txt, which consisted entirely of vision-model hallucination (an invented English-language title page, 'THE PRINCESS OF THE PAPIERES', with meta-commentary), with the standard illegible-page marker. The page is end-matter after FINIS; no Latin text was lost.


## 2026-07-10 — restored missing title page (W-audit fix)

The published English opened with only a truncated title fragment ending "for ..." — the entire title page was missing: the subtitle ("There is added the true method of making them, and the astonishing erection of the Signature of Mercury..."), the six-author block (Zoroaster the Chaldaean, Solomon King of the Jews, Raphael the Jew, Chael the Egyptian, Hermes the Persian, Thetel), the Trithemius-attribution line ("Drawn from a manuscript of Johannes Trithemius"), and the 1612 imprint. The ERRATA entry of 2026-06-09 documented a from-scratch re-translation of chunk_0001 to restore exactly this title page, but that correction never reached the shipped file. Restored the full title page into `chunks/full_chunk_0001.md` and `english.md` (from the parallel 70291 rendering of the same source, which carries the complete title block). Also removed vision-model blank-page narration ("Given these details: 1. This page contains nothing...") that preceded the title in `latin-ocr.txt` segment 3. The `grades.csv` ghost row for the nonexistent `full_chunk_0021` was removed, and the chunk-0001 note corrected.

