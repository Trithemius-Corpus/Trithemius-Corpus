# Errata — prdl-24376_ecloga-de-laude-calvorum-ad-carolum

## 2026-07-10 — shipped the Fable-5 facsimile re-translation (W5)

The facsimile re-translation documented in the 2026-06-09 entry below was present in version control (commit `3bdf641c3c`) but the shipped `english.md` / `chunks/full_chunk_0001.md` / `full_chunk_0002.md` were still the *superseded* earlier machine rendering. Restored the re-translated text from that commit. The `release-certification` rows in `grades.csv` (faithful 5.0, all three chunks) now correctly describe the shipped text. The earlier note below saying "the audit grades describe the superseded text, not the present text" is superseded by this restoration — the shipped text and the certified grades now agree. (The `english.md` header was also corrected: Tier C → Tier S, faithful 4.0 → 5.0, `LIMITATIONS.md` → `METHODOLOGY.md`, backend `gpt-v3` → `public`, matching `metadata.json` and the current corpus convention.) A seam-repair pass was applied (1 mid-sentence seam fixed).

## 2026-06-09 — full re-translation of both chunks (Fable 5 revision pass)

Both chunks were re-translated wholesale by Claude (Fable 5), working line by
line from the Bavarian State Library page scans rather than from the OCR alone.
The poem's constraint — every word begins with the letter c — plus the
high-resolution scans made most OCR damage recoverable.

This pass supersedes the earlier machine translation. The audit grades in
`chunks/grades.csv` describe the superseded text, not the present text, which has
not been independently re-audited. The superseded English is retained in version
control.

What changed, beyond general line-by-line fidelity:

- **chunk 1** — the epigraph's invented name "Donatus" removed (the print reads
  *Conatus*, the participle "attempting"); chapter 3's *Cincinnose caue*
  restored as the vocative taunt "Curly-locks, beware"; *caluaster* rendered as
  what it is (the mocker is himself balding); chapter 4's two `[unclear]`
  passages resolved from the scan (*cōscissa chorusco* = "slashed by the
  flashing blade").
- **chunk 2** — verse restored as verse (the prior text flattened or paraphrased
  it); chapter 5's `[unclear]` lines resolved (*Cōtrectās chalybem…* = the
  surgeon "handling the steel," with the cauterized neck and bloodletting
  read literally); chapter 6's "Cetam curuauit" treated as a print crux
  (probably *caelum*, "He arched the vault"); chapter 9's closing *celeste
  catinum* recognized as the "vessel of election" allusion (Acts 9:15) instead
  of two `[unclear]` brackets; chapter 10's "chariots" corrected to "curls"
  (print *curros* for *cirros*); chapter 12's *cosmi* (microcosm conceit)
  restored where the OCR read *colimi*.

Print cruxes that survive into the translation are flagged in a *Readings*
note at the end of each chunk; conjectures are identified as conjectures.

## 2026-06-10 — crypto-cluster prose re-translation (Fable 5, facsimile pass)

### full_chunk_0001
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** Two defects, both confirmed against the Bavarian State Library scan. (1) Chapter 1 line 5 ("Ceu crines capitis couellens crimina cordis.") was rendered "he plucks the purse from his heart." The print plainly reads "crimina cordis" (abbreviated crimĩa, c-r-i-m-tilde-i-a) = "the sins of the heart"; "purse" came from the OCR's misreading "crumia" and was an outright fabrication. (2) The translator's note claimed the print's chapter-4 final line read "capros" ('goats'); the scan plainly shows "Captiuos captat. captos ceruice coartat." with "captos" ('the captured'). The body already rendered it as "captured," so only the note was wrong.

**Key corrections (verified against the scan):**
- Line 40: 'he plucks the purse from his heart' -> 'he plucks out the sins of the heart' (print: crimina cordis; OCR 'crumia' is a misread)
- Translator's note: removed the false 'capros'/'goats' reading; recorded that the print reads 'captos' ('the captured'), and explicitly withdrew the prior note's error
- Translator's note: explicitly flagged the old 'purse from his heart' as a fabrication, now corrected
- Note updated to cite the scans checked and retained the honest 'crimine cluras' (~claras) and 'curros'/'cirros' and 'Conatus'-is-a-participle observations

**Surviving cruxes:**
- Prooemium line 5 ends 'crimine cluras' on the print — corrupt, likely for 'claras' (the bright Camenae); kept as an honest crux, not smoothed
- Chapter 4 has 'curros' for 'cirros' ('curls') — the print's own orthographic quirk, noted not silently fixed
- Whole poem is a tour-de-force C-acrostic; many OCR oddities are the 1496 print's own spellings, not transcription noise
