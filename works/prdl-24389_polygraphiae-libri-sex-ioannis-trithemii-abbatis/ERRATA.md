# Errata — prdl-24389

## 2026-06-10 — crypto-cluster prose re-translation (Fable 5, facsimile pass)

### full_chunk_0033
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The prior public rendering ended with a genuinely truncated, opaque clause ("'When she asks for papers to be hidden, tied to the leg,' and [unclear]") that misrepresented the segment boundary, and it silently normalized a print misprint without recording the crux. The segment is ordinary continuous prose: a chain of steganography anecdotes from Pliny (tithymalus/invisible milk-writing), Theodorus Bibliander's hyphasmaticon/hyphalmicon note, Herodotus on Demaratus' wax tablets and Gorgo's interpretation, Gellius 17.9 on Histiaeus' tattooed slave, Herodotus 1.123 on Harpagus' gutted hare to Cyrus (cf. Justin 1), the Mutina carrier-pigeons (Hirtius/Decimus Brutus), and secret inks, closing on an Ovid quotation. None of the prose was fabricated, but the ending and several proper names needed repair against the scans.

**Key corrections (verified against the scan):**
- Recovered the truncated ending from the scans: the segment closes mid-couplet on the hexameter only, 'Cum poscit cruri chartas celare ligatas,' = Ovid, Ars Amatoria 3.621; rendered it faithfully and reserved [unclear] for the deliberate mid-couplet cut (the pentameter 'Et iuncto blandas sub pede ferre notas' is the catchword 'Et iun-' on p.68 and belongs to segment 34), instead of the prior vague paraphrase 'papers to be hidden, tied to the leg'.
- Flagged the print crux at the Gorgo passage: the 1518 print itself reads 'Chromenis filia' (so the OCR is a faithful witness), a typographical error for 'Cleomenis'; restored the historically correct 'Gorgo, daughter of Cleomenes and wife of Leonidas' and recorded the misprint in the note (prior text emended silently).
- Verified and restored proper names against the print: Theodorus Bibliander, Demaratus, Susa, Xerxes, Histiaeus, Darius, Aristagoras, Astyages, Harpagus, Cyrus, Tithymalus; and noted that the print's 'Hyrcius'/'Decius Brutus' (siege of Mutina) are Hirtius and Decimus Brutus.
- Italicized the two run-in lemma headings per house style: 'The second kind: hyphasmaticon.' and 'Letters are likewise written in various other ways.'; tightened the Harpagus/Cyrus and Histiaeus passages for fidelity (e.g., 'tattooed the smooth head with the forms of letters', 'most trusted household huntsmen').

**Surviving cruxes:**
- Print reads 'Chromenis filia' — a 1518 misprint for 'Cleomenis' (Cleomenes); historical name restored, misprint noted.
- Segment 33 deliberately ends mid-couplet after the Ovid hexameter (Ars Am. 3.621); [unclear] marks the intentional cut at catchword 'Et iun-', not illegible print — the pentameter continues in segment 34.
- Print's 'Hyrcius' and 'Decius Brutus' = Aulus Hirtius and Decimus Brutus; restored with print forms noted.
- Pliny citation printed as 'lib. 26' for the tithymalus/invisible-writing detail; rendered as 'book 26' following the print.

## 2026-06-19 — [unclear] resolution pass (historical fact-checking)

**Editorial note:** The following [unclear] markers were resolved through historical
fact-checking against Trithemius scholarship and primary sources. These are editorial
completions, not translations — the original OCR could not read the damaged text, but
the names, dates, and places were identifiable from context.

**Sources:** Klaus Arnold, *Johannes Trithemius (1462-1516)* (Würzburg: Schöningh, 1991);
Trithemius, *Nepiachus* (autobiography); VD16 records; standard ecclesiastical history.

### full_chunk_0025
**Key corrections:** "abbot of [unclear]" → "St. James’s Abbey, Würzburg"

### full_chunk_0004
**Key corrections:** "Wimpfeling of [unclear]" → "Schlettstadt" (Wimpfeling’s birthplace, now Sélestat)

## 2026-07-09 — digitization-artifact cleanup (latin-ocr.txt)

- Removed a generation fill artifact (an asterisk run of ~4,000 characters) from [segment 122] of latin-ocr.txt. The run length (~4096) marks it as a model/pipeline artifact, not page content. Segment structure unchanged.

## 2026-07-09 — structural: removed-chunk placeholders restored

- Chunks [123, 124] were source-digitization boilerplate removed during the quality sweep; the files were deleted outright, leaving numbering gaps and dangling grade/chapter references. Restored them as standard removal-marker placeholder files (the same convention build_work_artifacts.py uses), so chunk numbering, chapter anchors, and the grade ledger resolve. No translation content was added; the reading text (english.md) is unchanged.

## 2026-07-11 — crypto-occult spot-check fixes

- Applied the previously documented resolution "abbot of [unclear]" -> "abbot of Saint James of Würzburg" to the chunk 0025 colophon line (the 2026-06-19 entry described this fix but it had not landed in the file).
