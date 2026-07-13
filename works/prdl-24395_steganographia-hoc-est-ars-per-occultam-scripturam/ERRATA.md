# Errata — prdl-24395 (Steganographia)

> **2026-06-10 — new work added to the corpus.** The *Steganographia* —
> Trithemius's most famous and most notorious work, the three-book cryptographic
> treatise disguised as angel-magic that the Church placed on the Index — was
> **not part of the original 46-work corpus**. The source could not be obtained
> during the first acquisition pass (Gallica returned the viewer HTML, not a
> PDF); it was recovered here from the **Bibliothèque nationale de France /
> Gallica** (Darmstadt/Frankfurt, 1621; ark `bpt6k5832538j`) by assembling its
> 168 IIIF page images into a PDF, the one-shot `.pdf` endpoint being
> rate-limited.

## Pipeline

- **OCR: Qwen2.5-VL-7B (local, Vulkan iGPU)** — the same model used to re-OCR
  every other work in the corpus, run via the resident multimodal `llama-server`
  (`scripts/reocr_full_server.py`). (An initial codex/GPT-5.5-vision OCR was
  discarded for methodology consistency; both produced comparable text on this
  blackletter.)
- **Translation: GPT-5.5 (codex) baseline, then a Fable 5 review-and-improve
  pass.** Fable, reviewing the GPT-5.5 output against the OCR and the page scans,
  produced a materially better translation and is the version shipped. The most
  consequential improvements, recurring across the book:
  - **Recovered the cipher tables.** GPT-5.5 repeatedly collapsed the per-chapter
    spirit-name tables (the *tabula directionis* and each prince's substitution
    table — the cryptographic substance of the work) into "[cipher table; see
    facsimile]" placeholders. Fable read them off the scans and rendered the
    actual spirit names and numeric keys (e.g. *Orpeniel 10 / Citgara 100 /
    Daniel 10*…), including the 31-spirit master key-table of Book I.
  - **Restored the German cover-text.** GPT-5.5 translated the Early-New-High-German
    vassal letters (Books I–II) into English; the German *is* the example
    cover-text the cipher rides on, so Fable restored it verbatim with a bracketed
    gloss.
  - **Fixed OCR-name and reading errors** GPT-5.5 carried verbatim —
    *Gabriel→Cabariel, Ratsiel→Raysiel, Vrisbhabens→"Vriel, habens", Gynos→servos*;
    flattened named winds (*Subsolanus, Vulturnus, Aquilo*) restored; *"Roth
    letters"* not *"Rota"*; *"liber familiaris"* = open letter not "familiar
    book"; and a GPT-5.5 hallucinated sentence (the Saturn/Pomiel passage) removed.

## Tier (C) — read with the crypto-occult caveat

Independent GPT-5.5 re-grade against the Latin: **faithful 3.92 / 5, hallucinated
61.6%**, → tier **C**. The *faithfulness* is A-level: the conjuration prose,
prefaces, and letters are well rendered. The high *hallucination* figure is the
documented crypto-occult artifact (cf. the Polygraphia/Clavis cluster and
LIMITATIONS §8): the OCR-referenced grader flags the preserved cipher tables and
the verbatim spirit-names / barbarous *voces magicae* as "content not in the
Latin," because a cipher table cannot be graded as faithful prose. The tier
therefore reflects the work's cipher density, not weak translation.

**Style C — added 2026-06-11.** The work now carries a full *Style C* cipher-key
rendering set (the corpus's structured treatment of the crypto-occult cluster):
the 39 cipher-table chunks — the master *Tabula Directionis* of Book I, each of
the ~30 spirit-princes' sub-spirit tables (chs. III–XXXI), the 31-spirit
recapitulation key-table, and the Book II hour-spirit tables — are rendered
table-by-table, each beside the source page facsimile, on the work's
[*Cipher-key tables*](prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam_style-c-cipher-key.html)
subpage. This is the proper scholarly presentation of the cipher material; the
**tier (C) is unchanged**, because it scores the *standard side-by-side reader*,
whose chunks still carry the tables inline — the Style C subpage is an additional
rendering, not a re-grade.

## Status

The cipher of the *Steganographia* itself is **not solved or decoded** here; the
Latin (and its German cover-text) is translated as it stands. For the
cryptography see the companion *Clavis* (`prdl-70281`/`prdl-70282`) and Reeds
(1998).

## 2026-06-19 — [unclear] resolution passes (multi-pronged)

Three passes reduced [unclear] markers across this work:

1. **Historical fact-checking** (12 fixes corpus-wide): proper nouns identifiable from Trithemius biography — "Abbot of [unclear]" → "St. James's Abbey, Würzburg", "Wimpfeling of [unclear]" → "Schlettstadt", "surnamed [unclear]" → "Magnus" (Charlemagne), "unwilling [unclear]" → "pupil" (Maximilian).

2. **False-positive removal** (7 fixes, prdl-70280): column-separator `[unclear]` markers in the ANNOTATIO SCRIPTORVM index were layout-parsing artifacts, not damaged words — removed.

3. **Mid-word line-break joining** (168 fixes corpus-wide): the vision OCR model inserted `[unclear]` at Fraktur line-break hyphenation points (e.g. `pri[unclear]mi` → `primi`). These were joined automatically by matching word fragments on either side of the marker.

**Total corpus-wide reduction: 35,577 → ~11,000 [unclear] markers (69% reduction).**

The remaining ~11,000 are genuinely damaged text where no model or method could recover the word. They are marked honestly.

## 2026-07-09 — digitization-artifact cleanup (latin-ocr.txt)

- Removed a generation fill artifact (an asterisk run of ~4,000 characters) from [segment 1] of latin-ocr.txt. The run length (~4096) marks it as a model/pipeline artifact, not page content. Segment structure unchanged.

## 2026-07-11 — chunk/segment misalignment repairs (chunks 0040, 0051; spot-check finding)

- **Chunk 0040** previously carried a duplicate translation of the Chapter XXVII (Soleuiel) material,
  whose Latin lives at segment 44 and which ships correctly at chunk 0044 — while chunk 0040's own
  Latin witness (segment 40: the close of the preceding chapter's Buriel conjuration, the arcanum
  example, and the "Salvator noster" letter specimen) was untranslated. Replaced with a fresh
  translation of segment 40, made directly against the Latin witness (Claude Fable 5, 2026-07-11);
  the letter specimen breaks off at the foot of the page in the source, marked in-text. The prior
  grades.csv row for this chunk describes the superseded (duplicate) text.
- **Chunk 0051** carried a variant duplicate rendering of the segment-55 passage ("I have read many
  most brilliant/splendid volumes...") under an illegible Latin witness (segment 51 is [illegible]).
  The passage ships correctly at chunk 0055; replaced chunk 0051 with the standard illegible-page
  marker. The prior grades.csv row describes the superseded text.
- **Chunk 0023** was reviewed for the same pattern and retained: its Latin witness (segment 23) is
  illegible, but the content (the twelfth dwelling, Cabariel/Circius chapter) is positionally correct,
  bracketed by mansio-chapter Latin in segments 22 and 25-26, and its conjuration repetition is
  source-backed (segment 25 carries the Cabariel formula three times).
