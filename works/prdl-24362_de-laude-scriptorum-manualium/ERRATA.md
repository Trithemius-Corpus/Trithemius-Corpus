# Errata — prdl-24362_de-laude-scriptorum-manualium

## 2026-06-19 — [unclear] resolution passes (multi-pronged)

Three passes reduced [unclear] markers across this work:

1. **Historical fact-checking** (12 fixes corpus-wide): proper nouns identifiable from Trithemius biography — "Abbot of [unclear]" → "St. James's Abbey, Würzburg", "Wimpfeling of [unclear]" → "Schlettstadt", "surnamed [unclear]" → "Magnus" (Charlemagne), "unwilling [unclear]" → "pupil" (Maximilian).

2. **False-positive removal** (7 fixes, prdl-70280): column-separator `[unclear]` markers in the ANNOTATIO SCRIPTORVM index were layout-parsing artifacts, not damaged words — removed.

3. **Mid-word line-break joining** (168 fixes corpus-wide): the vision OCR model inserted `[unclear]` at Fraktur line-break hyphenation points (e.g. `pri[unclear]mi` → `primi`). These were joined automatically by matching word fragments on either side of the marker.

**Total corpus-wide reduction: 35,577 → ~11,000 [unclear] markers (69% reduction).**

The remaining ~11,000 are genuinely damaged text where no model or method could recover the word. They are marked honestly.

## 2026-07-10 — removed modern calibration ruler from segment 21 (latin-ocr.txt only)

The final segment of `latin-ocr.txt` ended with OCR of a modern photographic color-calibration ruler, including the anachronistic copyright string `© 2007 digitalfoto-trainer.de`, after the genuine colophon (`Desideratus finis...Anno virginei partus.M.cccc.xciij.` / `Monasterij Chypensis.`) and the library stamp (`BIBLIOTECA REGIA / UNIVERSITATIS MONACENSIS`). The ruler was never translated (the English closes at chunk 0021 with the genuine colophon), so no English chunk was changed. Removed the ruler block from the tail of segment 21 only; segment count and all chunk boundaries unchanged.

## 2026-11-05 — AI scan-supported local correction batch

These are Codex AI visual assessments of BSB bsb00037424, not documented human review. Historical machine grades predate these edits. Original texts and exact file hashes are preserved in the correction ledger and snapshots.

### scribes-001

- Previous: I promised what I knew did not exceed the powers of my talent
- Local correction: I promised what I knew did exceed the powers of my talent
- Latin (expanded/normalized): promisi: quod ingenii mei vires excedere non ignoravi
- Source: BSB 2r (0005), [institutional image](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00037424_00005/full/full/0/default.jpg).
- Basis: The printed non qualifies ignoravi: I was not unaware that it exceeded my powers. The earlier English moves that negation onto exceeded.

### scribes-004

- Previous: Nor ought you to abandon the monastery for the sake of study
- Local correction: Nor is it necessary for you to leave the monastery for the sake of study
- Latin (expanded/normalized): Nec oportet vos propter studium monasterium deserere: quia unde proficiatis domi potestis invenire
- Source: BSB 19v (0040), [institutional image](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00037424_00040/full/full/0/default.jpg).
- Basis: The printed clause and its explanation support lack of necessity: the means of study can be found at home. This remains a contextual translation judgment, not a new prohibition.

### scribes-005

- Previous: Purge the [unclear] of your race
- Local correction: Cleanse the storehouse of your mind [ed.]
- Latin (expanded/normalized): Mentis vestre purgate horreum: et deus triticum faciet inferri scripturarum
- Source: BSB 19v (0040), [institutional image](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00037424_00040/full/full/0/default.jpg).
- Basis: The scan reads Mentis, not Gentis/Dentes, and horreum. The metaphor is the storehouse of the mind; neither race nor an illegible noun is needed.

The [ed.] marker replaces the resolved [unclear] marker to retain its annotation anchor and the numbering of later notes. It points to the scan-supported storehouse-of-the-mind correction above.

## 2026-11-17 — review against the Mainz print

Codex AI checked the following readings against the Bayerische Staatsbibliothek facsimile of BSB bsb00037424. Human review is pending.

### scribes-003

The edition previously read “my sight trembles; likewise my pen”. It now reads “my [dipped?] pen trembles again”.

*tremet [intinctus?] iterum calamus*. The verb tremet and the nominative calamus support a trembling pen. The word divided at the line ending is iterum. The sequence before it appears to read intinctus, a masculine participle that can describe a dipped pen. The earlier reading intuitus gave “my sight” more certainty than the type warrants. The brackets in the English mark the unresolved modifier. A Latin reader should adjudicate the letterforms, the syntax and the placement of iterum. [Printed folio 3v (0008)](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00037424_00008/full/full/0/default.jpg)

### A-F23

The edition previously read “Cassiodorus, Bede, Alcuin, Regino, Peter Damian”. It now reads “Cassiodorus, Bede, Alcuin, Rabanus, Regino, Peter Damian”.

*Cassiodorum, Bedam, Alcuinum, Rabanum, Reginonem*. The list prints Rabanum between Alcuinum and Reginonem. Both translations of this passage had skipped directly from Alcuin to Regino. [Printed folio 6v (0014)](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00037424_00014/full/full/0/default.jpg)
