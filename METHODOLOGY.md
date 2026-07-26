# Methodology

How the Trithemius Corpus was made, checked, revised, and presented. This page distinguishes the **recommended Trithemius 4B editions** from the earlier source-witness editions, explains what the grades mean, and states where machine-produced text still requires caution.

**Contents:** [What you are reading](#1-what-you-are-reading) · [Sources](#2-source-acquisition) · [OCR](#3-the-ocr-record) · [Translation](#4-the-translation-record) · [Pipeline](#5-pipeline-mechanics) · [Grading](#6-historical-automated-grading-and-current-review-status) · [Remediation](#7-the-remediation-record) · [Results](#8-results) · [Per-work provenance](#9-per-work-provenance) · [Special renderings](#10-special-scholarly-renderings-style-c) · [Limitations](#11-limitations-known-failure-modes) · [Responsible use](#12-what-this-corpus-is-good-for-and-what-it-is-not) · [Rejected approaches](#13-what-was-tried-and-did-not-ship) · [Reproducibility](#14-code-data-and-reproducibility)

## 1. What you are reading

The site now contains two related edition tracks.

### Recommended Trithemius 4B editions

The **Trithemius 4B edition** is the recommended English reading edition wherever one is available. There are 27 such editions. They use a corpus-trained **Qwen3-VL-4B “Trithemius” LoRA** OCR witness and a **GPT-5.5 dual-context** translation, independently assessed in a second pass by **Claude Sonnet 5**. Only works meeting the publication threshold were promoted.

These pages have also received an editorial formatting and quality pass. Visible scan-navigation clutter—page-number markers, blank-page notices, calibration-target notices, stamp text, and duplicate-scan notices—is removed from the reading view while retained in the archival source files. Uncertainty markers such as `[unclear]` remain visible. They are evidence of damaged or ambiguous source text and are preferable to invented certainty.

The T4B pages are formatted as continuous reading texts. Their source segment boundaries remain in the HTML for stable navigation and provenance, but they are not presented as artificial page divisions. Existing chapter maps drive the compact chapter navigator when a work has at least two valid chapter divisions.

### Earlier source-witness editions

The earlier edition track remains available for all 47 translatable printed witnesses. It was produced through several OCR and translation campaigns, principally CHURRO/Qwen vision OCR and GPT-5.5 revision, with targeted repairs by other models. These pages remain useful as independent witnesses, for comparison, and for works that do not yet have a publishable T4B edition.

The label **recommended source witness** identifies the preferred scan witness within a group of duplicate printed editions. It does not supersede the T4B reading recommendation.

### What is authoritative

Neither machine transcription is a critical Latin edition. The hierarchy is:

1. the institutional page facsimile;
2. the OCR witness shown on the site;
3. the English translation;
4. historical automated QA records, retained as triage evidence rather than certification.

For a passage used in publication, check the English against the Latin and the Latin against the facsimile.

## 2. Source acquisition

The corpus began with the PRDL author record for Johannes Trithemius and the bibliography at trithemius.com. Records were resolved to public-domain institutional scans from the Bavarian State Library, Herzog August Bibliothek, e-rara, dilibri, Internet Archive, Google Books, and Gallica. Duplicate records and editions were retained where they supplied genuinely separate witnesses.

The release contains 47 translatable printed witnesses representing 29 distinct texts. Four additional records are retained in the manifest as skipped because they are German-language or predominantly liturgical/tabular material. The *Steganographia*, initially blocked through the normal viewer route, was recovered through Gallica’s IIIF image service.

Every work’s metadata names its source institution and scan. The source scan, not the OCR, remains the final authority.

## 3. The OCR record

The project tested five main OCR generations.

| Generation | System | Role in the present site |
|---|---|---|
| 0 | Embedded PDF text / Tesseract 5.4 | Superseded except for one retained witness; useful as an audit baseline. |
| 1 | Qwen2.5-VL-7B | Part of the earlier hybrid witness for 14 works. |
| 2 | CHURRO-3B, a historical-print Qwen2.5-VL fine-tune | Earlier published witness for 31 works. |
| 3 | Base Qwen3-VL-4B-Instruct | Experimental and superseded. |
| 4 | Qwen3-VL-4B “Trithemius” LoRA | OCR witness for the 27 recommended T4B editions. |

Tesseract and embedded text fail systematically on early print: long *s* becomes *f*, abbreviations disappear, columns interleave, and damaged type produces nonsense. Vision models preserve page structure and early typography more effectively, though none is immune to repetition, truncated dense pages, misread names, or invented-looking letter sequences.

The T4B LoRA was trained on page/transcription pairs drawn from this corpus. A later audit corrected an early interpretation of its quality. The initial report attributed too much of the rejected translation lane’s failure to OCR. Direct review showed that the LoRA’s body-page OCR was generally clean—typically better than 97% non-degenerate in the hardest audited works. The more serious defect was downstream translation drift in a run that lacked strict output guards.

Roughly 58 LoRA pages reached the original 3,000-token output cap. Some are true truncations; others are repetition loops for which a larger token allowance would merely produce a longer loop. Where a second witness could resolve the text, it was used during repair. Where both witnesses were damaged, the reading text retains an uncertainty marker.

## 4. The translation record

### Earlier edition track

The earlier translations were built through multiple campaigns. MiniMax-M2.7, Claude Opus 4.7, and a local Gemma model produced early drafts. GPT-5.5 then audited and retranslated the corpus at high reasoning effort, winning 3,662 of 3,705 recorded keep-better contests. Later CHURRO re-OCR translations, Opus pairwise adjudication, GLM tail-gap closure, and Claude facsimile-based repairs improved individual passages.

This history matters because the earlier reading text is a documented per-chunk selection, not the output of one uninterrupted model call.

### Trithemius 4B edition track

The T4B lane pairs the corpus-trained LoRA OCR with GPT-5.5 translation in dual-context mode. Dual context gave the translator broader continuity across page groups, but the original batch ran without the strict content-fidelity guards later shown to be necessary. Its characteristic failures were:

- page drift: fluent translation of the wrong source page;
- fabrication when a source page was empty or unusable;
- repeated phrases or enumerative loops;
- dropped or mismatched page markers;
- leaked model preambles or structured-output fragments.

These failures were not evenly distributed. Claude Sonnet 5’s complete second-pass assessment found 27 works at publishable S/A quality even though the lane as a whole could not be promoted. Those 27 became the T4B editions. Lower-scoring works remain withheld.

After promotion, the First-time-in-English T4B works were read in full where practical, followed by the crypto-occult group and a wider structural sweep. Repairs addressed repeated phrases, duplicated endings, leaked model text, page-boundary omissions, genuine OCR gaps, and scan duplication. Parallel editions were used as secondary evidence when available. Unresolvable damage was marked rather than silently reconstructed.

## 5. Pipeline mechanics

The earlier pipeline chunks OCR text at approximately 4,500 characters, preferring paragraph and page boundaries and never splitting words. A noise guard excludes material with too little alphabetic content. Translation prompts request clear modern English, preservation of names, dates, citations, and structure, expansion of common early-modern abbreviations, and explicit `[unclear]` marking where the OCR does not support a reliable reading.

The T4B assembler retains numbered source segments for provenance. During site rendering, formatting-only scan notes are filtered from the visible English without altering `works-t4b/<id>/english.md`. This separation is intentional: archival artifacts remain inspectable, while readers receive a clean continuous text.

The strengthened dual-lane guards now test:

- source/translation content overlap;
- survival of extractable names, dates, and anchors;
- page-marker mismatches when paired with low content overlap;
- suspicious repetition and output-format leakage.

The overlap check normalizes common long-*s* OCR artifacts and compares Latin content stems with the translation. In calibration, faithful chunks showed meaningful overlap while drifted chunks clustered near zero. These guards are used for audit and future reruns; they were not retroactively treated as proof of correctness.

## 6. Historical automated grading and current review status

The public site no longer presents machine-generated `S/A/B/C/F` tiers. Those
labels overstated what automated comparison could establish and blurred the
difference between readable output, model agreement, editorial preparation,
and human verification. Historical grades remain in metadata and audit ledgers
for reproducibility.

Current public pages report four independent facts: text origin, documented
human review, editorial state, and automated-QA coverage. Internally, an
unreviewed machine translation begins at triage status C. Promotion requires
documented human comparison against the cited witness.

Different graders served different purposes.

- **Claude Sonnet 5** is authoritative for the T4B publication decision. Its second pass covers the full graded T4B set.
- **Claude Sonnet 4.6** supplied most independent per-chunk grades for the earlier edition track.
- **Claude Opus 4.7/4.8** handled targeted review and pairwise keep-better adjudication.
- **GPT-5.5** performed the major audit-and-retranslate campaign.
- **MiniMax-M3 and GLM-5.2** supplied independent hunting and comparison signals. MiniMax’s T4B assessment was retained as a dual check, not as the final authority.
- **MiniMax-M2.7 self-grades** are historical evidence only. Their overconfidence demonstrated why translator self-grading is inadequate.

The historical tier formula used the worse result of a faithfulness floor and hallucination cap:

| Tier | Mean faithfulness | Hallucination |
|---|---:|---:|
| **S** | at least 4.0 / 5 | at most 5% |
| **A** | at least 3.5 / 5 | at most 15% |
| **B** | at least 3.0 / 5 | at most 30% |
| **C** | at least 2.5 / 5 | — |
| **F** | below 2.5 / 5 | — |

T4B publication originally required Sonnet faithfulness of at least 3.5. These
scores now remain historical triage records only; they do not promote an edition
or guarantee any sentence.

## 7. The remediation record

The corpus has undergone several distinct repair campaigns.

**Hallucination remediation.** A dual-grader consensus sweep identified 81 unsupported chunks across 20 earlier-track works. Fabricated prose was replaced by faithful text or explicit illegibility markers and rechecked.

**Tail-gap closure.** A set of 184 source segments across six works extended beyond the earlier English track. These were translated and spliced into the aligned reading text.

**Double-scan deduplication.** Two large chronicles contained page ranges digitized twice. Per-chunk grading did not detect this because both translations were faithful to duplicated OCR. A structural audit resolved 152 duplicate segment pairs while preserving stable numbering and source transparency.

**T4B full-work review.** The First-time-in-English editions received priority, followed by crypto-occult works and the remaining published T4B set. Solvable defects were corrected against local context, page boundaries, and alternate witnesses. This included removal of a 50-fold repeated phrase in *Sui Ipsius Vindex*, duplicated prophecy and conclusion material, wrong-page prose, leaked JSON/preambles, and several recoverable `[unclear]` gaps. Genuine damaged names, ownership inscriptions, tables, and passages unreadable in both witnesses remain marked.

All content-level repairs belong in the source or its provenance record. Display-only cleanup—such as hiding `--- Page N ---`—occurs at render time and does not rewrite the archival transcription.

## 8. Results

The site currently presents:

- **47** translatable earlier-track printed witnesses representing **29** distinct texts;
- **27** recommended Trithemius 4B editions that passed the Sonnet publication review;
- **26** cross-links from matching earlier work pages to their T4B editions, plus one T4B scan represented only in the T4B index;
- **23** texts identified as First-time-in-English at the distinct-text level;
- a homepage “Start here” selection containing 12 distinct First-time-in-English works.

The earlier track's canonical historical ledger contains 4,400 chunks, 4,353
machine-graded. Its former scoreboard reported S=47 and mean model-assessed
faithfulness of 4.63/5 after remediation. Those figures describe an automated
pipeline state, not human verification, and are no longer used as headline
quality claims.

The T4B editions provide prepared reading views where their structure permits.
They are not labeled as human-verified or recommended on the strength of model
scores. Earlier editions remain valuable independent witnesses and should be
consulted where any reading text is uncertain.

## 9. Per-work provenance

Each earlier work directory contains `metadata.json`, `latin-ocr.txt`, `english.md`, chunk files, grades, chapter data where available, and `ERRATA.md`. The corpus-level `manifest.json` and quality ledgers provide machine-readable summaries.

Each T4B directory under `works-t4b/` contains its LoRA OCR witness, assembled
English, metadata, chunk material, and introduction. Its page identifies the
edition as **Trithemius 4B** and reports origin, review status, editorial state,
and automated-QA coverage. Historical Sonnet scores remain in provenance data.

Authorship and assembly are credited to **Ian Carlos Fabin** (Carlosian), with the public profile at [github.com/agentcarlosian](https://github.com/agentcarlosian).

## 10. Special scholarly renderings (Style C)

Twenty-three earlier-track works include enhanced Style C renderings for material poorly served by ordinary paragraph translation: cipher tables, acrostics, alphabets, diagrams, catalogues, verse, and other layout-dependent passages. These renderings preserve the relationship between transcription, translation, and facsimile more explicitly than the continuous reader.

The former site-wide “Scholarly” viewing toggle has been removed. Specialized Style C pages remain linked where they add real value; uncertainty annotations are visible in the ordinary reading view instead of being hidden behind a mode.

## 11. Limitations: known failure modes

### OCR damage

Names, abbreviations, marginalia, tables, Greek, Hebrew, cipher alphabets, and worn first or final leaves remain difficult. A fluent translation cannot repair letters that are absent from every witness.

### Uncertainty markers

`[unclear]` and related brackets are editorial honesty markers, not unfinished UI. Some were resolvable through alternate witnesses and have been repaired. The remainder should stay visible until better evidence is available.

### Repetition loops

Vision OCR and translation models can repeat a phrase, line, name, or list many times. Mechanical screens and full-work reading caught known severe cases in the published T4B set, but short plausible repetitions still require judgment.

### Page drift

Long contextual translation can continue fluently from neighboring material while losing alignment with the current page. Content-overlap and anchor guards now detect many such cases. The original T4B batch predated those strict guards, so publication depended on independent grading and subsequent review.

### Tables and cryptographic apparatus

Prose-oriented translation can flatten or omit structured content. Consult Style C, cipher pages, or the facsimile for alphabets, substitution tables, spirit-name lists, and layouts where position carries meaning.

### Preamble and formatting leakage

Models sometimes emit “Here is the translation,” JSON fragments, or internal instructions. Known T4B leaks were removed during review. Report any survivor as an erratum.

### Latin-only display segments in the parallel viewer

The parallel viewer is source-preserving. If a Latin display segment has no usable English, the Latin remains visible and the English cell is marked. Duplicate-scan segments may point to the retained translation. This is a property of the digitized witness, not necessarily a broken page.

### Presentation versus archive

T4B page markers and scan notices are hidden in the reading interface, but retained in archival Markdown. Readers needing page-level reconstruction should consult the source files and facsimile rather than infer printed pagination from the continuous view.

## 12. What this corpus is good for, and what it is not

The corpus is well suited to discovery, continuous reading, comparison across witnesses, searching Trithemius’s vocabulary and themes, locating passages for closer study, and gaining access to works not previously available in published English.

It is not a substitute for a critical Latin edition, palaeographic judgment, or source verification in a scholarly quotation. The labels “recommended” and “S/A” identify the best available machine-assisted reading path within this project; they do not convert it into an authoritative human edition.

For responsible use:

1. begin with the T4B edition where available;
2. compare the earlier witness when the T4B text is uncertain;
3. check consequential claims against the Latin;
4. check disputed Latin against the page image;
5. cite the specific edition and disclose machine assistance where appropriate.

Corrections are welcome through the repository. A useful report names the work, segment or quoted phrase, the problematic English, and the supporting Latin or facsimile evidence.

## 13. What was tried and did not ship

Negative results are part of the method.

- **The complete unfiltered T4B lane did not ship.** The LoRA OCR was better than the first failure analysis suggested, but the unguarded translation batch contained clustered drift and fabrication. Only the 27 independently publishable works were promoted.
- **A guarded GPT-5.6-sol rerun was tested but not adopted as a replacement corpus.** On the difficult *Compendium*, strict guards accepted 57 of 104 chunks and correctly blocked 47 drifted outputs; a sermons rerun remained partial. This demonstrated the value of guards but did not yield a complete edition.
- **A fully local NPU translation lane** was rejected for fidelity and repetition problems.
- **Unlimited-OCR** was rejected because plausible word-level corruption was worse than explicit uncertainty.
- **Retrieval augmentation** did not measurably improve failing chunks; damaged OCR, not missing topical context, was usually the binding constraint.
- **Automatic inline cipher decryption** was kept separate from the reading text. Recovered mechanisms and plaintext belong on the cipher-solutions pages.
- **Automatic multi-witness conflation** was rejected. Separate printed witnesses remain separate rather than being silently merged into a synthetic critical text.

## 14. Code, data, and reproducibility

Site construction, edition assembly, validation, and audit scripts are in `scripts/`. Canonical quality data are in `data/_quality/`; earlier editions are in `works/`; T4B source editions are in `works-t4b/`; and corpus metadata are in `manifest.json` and `CITATION.cff`.

A complete site build runs:

```text
python scripts/build_site.py
python scripts/build_t4b_pages.py
npx pagefind --site site/dist
python scripts/validate_release.py
```

The site can be rebuilt from the repository. The full OCR and translation production environment is documented but not turnkey: it depended on public institutional scans, local and cloud vision inference, and several commercial model APIs. Large page-image caches and private working-lane artifacts are not all included in the release.

The release validator checks relationships among metadata, chunk ledgers, grades, chapter anchors, generated pages, and the search index. Validation guards against internal inconsistency; it does not replace philological review.

*Acknowledgment: Stephen Skinner and Daniel Clark’s 2024 edition of the* Steganographia *was an important reference for the cryptographic corpus. Scriptural and patristic retrieval anchors drew on public-domain Vulgate, Douay-Rheims, NPNF, and ANF materials.*

— Ian Carlos Fabin, 2026
