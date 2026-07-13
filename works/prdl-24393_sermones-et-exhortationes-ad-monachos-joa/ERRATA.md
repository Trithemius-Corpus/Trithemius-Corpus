# Errata — prdl-24393

## 2026-06-09 — targeted chunk re-translation (Fable 5 revision pass)

### full_chunk_0127

Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control. The audit row for this chunk in `chunks/grades.csv` describes the superseded text.

**What was wrong:** The published rendering opened with a fabricated psalm citation, "Have mercy on me, O God," which the print does not contain; the page opens mid-word "(no)stra tẽptatio est tota sup terrã," and the real psalm citations (Ps 29:8; Rom 9:16) occur only inside the fifth cause. The old version also scrambled the print's paragraph order (relocating the psalm material and the "causes in order" transition to the top, merging the fifth cause into the fourth) and dropped both patristic attributions (Pope Leo; Gregory).

**Key corrections (verified against the scan):**
- Removed the unwarranted opening 'Have mercy on me, O God': verified page 150 begins '(no)stra teptatio est tota sup terra' (continuation of 'Vita enim no-' from p. 149), rendered '[For our life] is wholly a temptation upon the earth'
- Restored print order: Quarto (self-will) -> Quinto (presumption of merits, with the Ps 29:8 / Rom 9:16 citations in situ) -> transition -> four causes of temporary withdrawal -> two preservation precautions; old version had merged Quinto into Quarto unnumbered and moved its citations to the chunk opening
- Restored the Leo attribution: 'ibiqz vt sact9 papa dicit leo' = 'and there, as the holy Pope Leo says, we run into the danger of failing, where we call back the appetite for advancing' (old version dropped 'Leo')
- Recovered the closing Gregory attribution: 'Na vt diu9 Gre. dicit: spoliari desiderat: q thesauru i publico portat' = 'as Saint Gregory says, he who carries his treasure in public desires to be robbed' (cf. Greg. Hom. in Ev. 11); old working version missed the attribution and the public-repo 0127 rendering ('God does not wish the grace given by him to be stripped away...') was wrong
- 'q aliter viues qz promisit dno metitur' (glyph 'q̃z promisit' verified) = 'living otherwise than he promised, lies to the Lord'; old rendering garbled this clause
- 'dei gratiam iustissime amittit' = 'most justly loses' (old: 'very quickly')
- 'Negociamini precor dum tempus est' = 'Trade, I beg you, while there is time'; old 'Trade with God's talents' invented 'God's talents'
- 'Nemo ei deuot9 meritis suis: nemo sctus virib9 proprijs' = 'no one devout by his own merits, no one holy by his own strength' ('sctus'='sanctus', same abbreviation as 'sctus ppheta' three lines above); old version relocated and rendered 'strong'
- 'dnm iesum pro consolaciunculis querunt' = 'seek the Lord Jesus for the sake of petty consolations' ('Iesum' omitted in both prior versions; diminutive restored)
- 'vt ois iactatia caueatur' = 'that all boasting be avoided' (old: 'empty chatter')
- 'ex consuetudine vnu magnu efficit' = 'out of habit brings about one great one' (OCR garbage 'ex p̄luerī die rūnī' resolved from scan)
- 'in sancta compunctione' = 'in holy compunction' (public 0127 had 'dry compunction', unsupported)
- Printer's signature 'm iiij' (OCR misread 'vi vi') recorded as a bracketed editorial line

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'ibiqz' vs 'vbiqz' (ibique/ubique) introducing the Leo citation - first letter not fully resolvable at scan resolution; ibi...ubi correlative adopted
- 'dulcedine pntis spualis consolat~' - elliptical; final abbreviated verb read as 'consolatur', rendered 'consoles with the sweetness of his spiritual presence' (slightly interpretive)
- 'necessaria d~r' expanded as 'dicitur' ('is said to be necessary')
- '[For our life]' supplied editorially - the sentence's subject 'Vita enim no-' stands on the preceding page, outside this segment's span
- 'q~' in 'in qua q~ no pgredimur' read as 'qui' (could be 'quando'); sense identical
