# Errata — prdl-24386

## 2026-06-09 — targeted chunk re-translation (Fable 5 revision pass)

### full_chunk_0065

Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The old translation smoothed garbled OCR into confident but unsupported prose: it invented an imperative "wound me" from the broken word "ani|me vulnerate" (the tail of "make a plaster for your wounded soul" from the previous chunk), rendered "modo dum loqueris" (even now, while you speak) as "at death," turned "dum prodest … dum cauen[di oportunitas adest]" into the invented adverbs "prudently … cautiously," and dropped the clause "the sixth root of fear is raised up in the mind of the one who meditates." Several smaller phrases ("supreme justice," "their portion," "all the consolation") had no warrant in the print.

**Key corrections (verified against the scan):**
- Opening 'me vulnerate' verified as the tail of 'emplastrum fac ani|me vulnerate' (wounded soul), continuing the previous chunk — not the imperative 'wound me'
- 'quid tibi sit allatura dies crastina penit9 ignoras' = 'penitus' (you are utterly ignorant of what tomorrow may bring) — not 'for repentance'
- Restored omitted clause: 'Sexta radix timoris in mente meditantis erigitur' — the sixth root OF FEAR is raised up IN THE MIND OF THE ONE WHO MEDITATES
- 'Cuncta sub ancipiti pendent mortalia casu et spondent propria mobilitate fugam' — mortal things HANG (pendent) and 'promise flight by their own changeableness', not 'stand ... promise only fleeting spans'
- 'aut modo dum loqueris desinet esse tuum' — 'even now, while you are speaking, it will cease to be yours' — public's 'at death' unsupported
- 'sanctis in celo' (abbreviated sc-tis) — 'the saints in heaven', and 'laboriosus et carni contrarius contemptus seculi' is one noun phrase (the contempt of the world, once toilsome and contrary to the flesh), not three separate nouns
- 'et qui multis et qui paucis vixere temporibus' — 'they who lived for many seasons and they who for few', not 'the many and the few who lived'
- 'premia diversa iusticia dictante perceperunt' — 'diverse rewards at the dictate of justice'; public's 'supreme justice'/'their portion' unsupported
- Final sentence: 'Hec cogita dum prodest: hec meditare dum cauen-' breaks mid-word at the page foot; the turn-over '(di oportunitas adest' verified at the head of page 74 — 'while it avails ... while the opportunity of taking heed is at hand', not 'prudently ... cautiously'
- 'Multos spes vite longioris ad interitum pertrahit: quia ...' — present tense 'drags', causal 'because'
- Page mapping corrected: the chunk is carried by page 73, not page 74 (page 74 carries Radix vii)

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'pertrahit' vs 'pertraxit/pertrabit' — h/b ambiguous in the type; read as present 'pertrahit' (conjectural)
- 'penitentis' vs 'penitenti' — terminal abbreviation stroke after 'penitent-'; rendered as genitive 'the penitent's humble confession' (conjectural)
- Chunk boundaries cut mid-word at both ends: opens at 'ani|me vulnerate' (previous chunk) and ends at 'cauen-' whose completion 'di oportunitas adest' is a printed turn-over belonging to the next chunk

## 2026-06-19 — [unclear] resolution passes (multi-pronged)

Three passes reduced [unclear] markers across this work:

1. **Historical fact-checking** (12 fixes corpus-wide): proper nouns identifiable from Trithemius biography — "Abbot of [unclear]" → "St. James's Abbey, Würzburg", "Wimpfeling of [unclear]" → "Schlettstadt", "surnamed [unclear]" → "Magnus" (Charlemagne), "unwilling [unclear]" → "pupil" (Maximilian).

2. **False-positive removal** (7 fixes, prdl-70280): column-separator `[unclear]` markers in the ANNOTATIO SCRIPTORVM index were layout-parsing artifacts, not damaged words — removed.

3. **Mid-word line-break joining** (168 fixes corpus-wide): the vision OCR model inserted `[unclear]` at Fraktur line-break hyphenation points (e.g. `pri[unclear]mi` → `primi`). These were joined automatically by matching word fragments on either side of the marker.

**Total corpus-wide reduction: 35,577 → ~11,000 [unclear] markers (69% reduction).**

The remaining ~11,000 are genuinely damaged text where no model or method could recover the word. They are marked honestly.
