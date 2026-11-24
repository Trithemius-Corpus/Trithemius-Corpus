# Errata — prdl-24390_polygraphiae-libri-vi

## 2026-06-19 — [unclear] resolution pass (historical fact-checking)

**Editorial note:** The following [unclear] markers were resolved through historical
fact-checking against Trithemius scholarship and primary sources. These are editorial
completions, not translations — the original OCR could not read the damaged text, but
the names, dates, and places were identifiable from context.

**Sources:** Klaus Arnold, *Johannes Trithemius (1462-1516)* (Würzburg: Schöningh, 1991);
Trithemius, *Nepiachus* (autobiography); VD16 records; standard ecclesiastical history.

### full_chunk_0001
**Key corrections:** "Abbot of [unclear]" → "St. James’s Abbey, Würzburg"

### full_chunk_0111
**Key corrections:** "abbot of [unclear]" → "St. James’s Abbey, Würzburg"

### full_chunk_0006
**Key corrections:** "surnamed [unclear]" → "Magnus" (Charlemagne)

## 2026-06-19 — [unclear] resolution passes (multi-pronged)

Three passes reduced [unclear] markers across this work:

1. **Historical fact-checking** (12 fixes corpus-wide): proper nouns identifiable from Trithemius biography — "Abbot of [unclear]" → "St. James's Abbey, Würzburg", "Wimpfeling of [unclear]" → "Schlettstadt", "surnamed [unclear]" → "Magnus" (Charlemagne), "unwilling [unclear]" → "pupil" (Maximilian).

2. **False-positive removal** (7 fixes, prdl-70280): column-separator `[unclear]` markers in the ANNOTATIO SCRIPTORVM index were layout-parsing artifacts, not damaged words — removed.

3. **Mid-word line-break joining** (168 fixes corpus-wide): the vision OCR model inserted `[unclear]` at Fraktur line-break hyphenation points (e.g. `pri[unclear]mi` → `primi`). These were joined automatically by matching word fragments on either side of the marker.

**Total corpus-wide reduction: 35,577 → ~11,000 [unclear] markers (69% reduction).**

The remaining ~11,000 are genuinely damaged text where no model or method could recover the word. They are marked honestly.

## 2026-07-10 — collapsed `omission;` x26 stutter loop (chunk 28; audit fix)

Chunk 028 of the Ave Maria cipher word-bank contained a line where the OCR had read a damaged/blank Latin line as `omissione` x26; the translator rendered all 26 as `omission; omission; ...`. Collapsed to a single honest illegible-line marker in chunk 028, english.md, and latin-ocr.txt. Same defect pattern as the `CHEMISTRS` loop fixed in prdl-24391 on 2026-07-09. (Audit finding H1.)

## 2026-07-11 — crypto-occult spot-check fixes

- Applied the previously documented resolution "abbot of [unclear]" -> "abbot of Saint James of Würzburg" to the chunk 0001 title line and the chunk 0111 colophon (removing the half-applied gloss "that is, Würzburg, at St. James"); the 2026-06-19 entry described these fixes but they had not landed in the files.

## 2026-11-23 · polygraphia-austrasia

The s entry in the left column is the historical region Austrasia, in the accusative. The neighbouring entries are Gascony and Gaul. AI scan collation. No human verification of this correction is documented.

Previous wording: s Australia

Revised wording: s Austrasia

*r gasconiam, s austrasiam, t galliam*. [Bayerische Staatsbibliothek, München, bsb00029406, canvas 186, corpus image 187](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00029406_00186/full/1000,/0/default.jpg).


## 2026-11-23 · polygraphia-belgica

The q entry in the right column is Belgica. It was missing from the English, shifting the later right-hand entries out of alignment with the letters in the left-hand column. AI scan collation. No human verification of this correction is documented.

Previous wording: p [unclear] r Navarre

Revised wording: p [unclear] q Belgica r Navarre

*p buconiam, q belgicam, r nauarram*. [Bayerische Staatsbibliothek, München, bsb00029406, canvas 186, corpus image 187](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00029406_00186/full/1000,/0/default.jpg).

The exact image for this geography table is BSB canvas 186, corresponding to corpus image 187. The earlier OCR reading *australia* is preserved in the archived transcription. The corrected English and the cited image identify *austrasiam* at left s and *belgicam* at right q. [Basel 1518, BSB canvas 186](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00029406_00186/full/1000,/0/default.jpg)

## 2026-11-23 · key-numeral-cipher

The type on C ii verso gives i&kahk, &kif and icei&kaib. C ii recto assigns the cipher group i& to q and the single ampersand to f. The open-foot h can be distinguished from the closed b in the same lines. The inter-group punctuation is regularized and the line breaks are represented by spaces. The unusual i&kahk is transcribed as printed. The BSB copy agrees with HAB Fb 128 on these letters. The dot or small stroke following ibeicdaka is treated as a separator. AI visual collation. Human review is undocumented.

Previous wording: Iaaibid ifeib, ieifeigeicbkib. cakeibid. ikabk. gidibid. eigih. iceigigh ibkig. kif. iaaihifid, ibeicdakaieb. icei kaib.

Revised wording: Iaaihid ifeib, ieifeigeicchkib. cakeihid. i&kahk. gidibid. eigih. ieeigigh ibkig. &kif. iaaihifid, ibeicdaka eih. icei&kaib.

[Bayerische Staatsbibliothek, München, Basel 1518, sig. C ii verso](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00029406_00536/full/full/0/default.jpg) · [Numeral alphabet](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00029406_00535/full/full/0/default.jpg)
