# Scholarly Reader Quality Roadmap

Status: approved for implementation

Planning baseline: 2026-07-25
Scope: browser reading, scholarly presentation, facsimile integration,
publication formats, and text visualization

## 1. Purpose

The Trithemius Corpus should become a durable, inspectable digital reading
edition rather than merely a set of translated files rendered as web pages.
Its interface must serve four activities without confusing them:

1. reading Trithemius in clear modern English;
2. checking the English against the Latin;
3. checking both texts against a specific printed witness; and
4. exploring relationships that are difficult to see in linear prose.

The governing rule is that every analytical or visual layer must lead back to
citable source evidence. A visualization may suggest a pattern; it must never
silently become the textual authority.

## 2. Current baseline

The repository currently contains:

- 47 digitized printed witnesses representing 29 distinct texts;
- 7,827 source pages and approximately 4,393 reader segments;
- a chapter map and institutional source link for every witness;
- ten texts represented by multiple witnesses, with as many as six witnesses
  for one text;
- continuous English reading pages and Latin/English parallel pages;
- Pagefind full-text search, four themes, adjustable typography, print styles,
  reading progress, keyboard navigation, and browser speech synthesis;
- specialized Style C renderings for 23 works; and
- a cipher lab, solved-cipher presentations, and curated facsimile crops.

The important presentation constraints are:

- the site must remain deployable as static files;
- `site/dist/` is committed build output and cannot be regenerated in CI
  without the separate working corpus;
- existing Markdown, OCR, chunks, grades, and errata are part of the release
  record and must not be silently replaced;
- institutional images have differing rights statements and API versions;
- OCR variation must not be mistaken for witness variation; and
- the English remains a machine-assisted provisional reading text unless a
  stronger human-review claim is explicitly recorded.

## 3. Product model

Each work will ultimately have four coordinated views.

### Read

A quiet, reflowable English reader. Editorial interventions remain discoverable
without overwhelming ordinary reading. This remains the default view.

### Study

English and Latin synchronized at stable passage boundaries, with optional
editorial notes, uncertainty, named entities, references, and witness variants.

### Source

A zoomable facsimile synchronized to the active passage. Where positional OCR
exists, selecting text highlights the corresponding printed region and
selecting a region locates the text.

### Explore

Purpose-built analytical views: cipher traces, witness comparison,
concordances, timelines, maps, and carefully labeled semantic discovery.

All four views must preserve the same passage identity when the reader switches
between them. View state must be expressible in the URL so a reader can cite,
bookmark, and share exactly what they are seeing.

## 4. Architectural direction

### 4.1 Static-first, progressively enhanced

The generated HTML is the publication. JavaScript enhances it but is not
required to read or cite the text. Search data, annotations, IIIF manifests,
TEI exports, and EPUB packages are generated during the build.

This avoids a service dependency, retains GitHub Pages compatibility, supports
indexing and archiving, and keeps the corpus usable when an experimental
visualization fails.

### 4.2 One stable passage model

The source representation needs stable identifiers below the chapter level.
The first implementation will use a compact generated JSON record rather than
attempting an immediate corpus-wide TEI conversion.

Proposed logical record:

```json
{
  "id": "trc:prdl-24395:witness:seg-0088:p-0003",
  "work_id": "prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam",
  "witness_id": "prdl-24395",
  "chapter_id": "ch-88",
  "segment": 88,
  "sequence": 3,
  "languages": {
    "la": "...",
    "en": "..."
  },
  "source": {
    "canvas": "https://example.org/iiif/canvas/123",
    "page_label": "123",
    "selector": "xywh=120,340,880,190"
  },
  "annotations": []
}
```

The exact storage shape may change during the pilot. The invariants are:

- IDs are deterministic and do not depend on rendered page height;
- identifiers survive typography and template changes;
- Latin, English, scan targets, and annotations point to the same passage;
- generated records state their source and transformation version; and
- old links continue to resolve when a model version changes.

### 4.3 Standards and interchange

The project will use:

- TEI P5 for scholarly interchange and eventual durable textual encoding;
- IIIF Presentation API 3 for witnesses, canvases, ranges, and annotation
  layers;
- IIIF Content Search API 2 for interoperable passage search;
- W3C Web Annotation for notes, corrections, and selectors;
- DPUB-ARIA 1.1 and WCAG 2.2 for publication semantics and accessibility;
- EPUB 3.3 for downloadable reflowable editions; and
- CSS Paged Media through Vivliostyle for controlled print/PDF output.

The repository will not adopt TEI Publisher or another server platform during
this sweep. A small TEI profile will be exported and validated first. The team
can revisit a larger platform only after the passage and facsimile model proves
it adds more value than operational cost.

## 5. Editorial layer model

Presentation must distinguish these layers:

1. source image;
2. diplomatic or source-faithful OCR transcription;
3. normalized or corrected Latin, where one exists;
4. English translation;
5. editorial notes, gaps, corrections, and conjectures;
6. witness variation; and
7. derived interpretation such as entities, similarity, or topics.

Each layer must identify its provenance. Interface controls may hide layers for
readability, but hidden uncertainty must remain signaled and reachable.

Suggested TEI subset for the pilot:

- `div`, `head`, `p`, `list`, `item`, `table`, and `row` for structure;
- `pb` and `facsimile/surface/zone` for witness linkage;
- `seg` with stable `xml:id` and cross-language correspondence;
- `unclear`, `gap`, `choice/sic/corr`, and `note` for editorial state;
- `persName`, `placeName`, `orgName`, and `ref` for controlled entities; and
- `listWit`, `app`, `lem`, and `rdg` for validated witness variation.

## 6. Implementation program

Each item is a separate reviewable pull request. Later branches are created
from the newly updated `main` after their prerequisite merges. The preserved
`claude/trithemius-editorial-audit-d5c924` branch remains an untouched reference.

### PR 1 — Reader quality baseline

Proposed branch: `codex/reader-quality-baseline`

Deliverables:

- document this roadmap and the supported reader behaviors;
- define representative fixtures for short prose, very long prose, complex
  cipher apparatus, and multiple witnesses;
- add deterministic source-level checks for landmarks, headings, languages,
  controls, fragment targets, and reader-script contracts;
- add a browser audit path that can be run locally when Chrome or Chromium is
  present;
- correct low-risk semantic and accessibility defects exposed by the checks;
- ensure reduced-motion, keyboard, focus, narrow reflow, and JavaScript-free
  reading have explicit acceptance criteria; and
- reconcile reader code with the published methodology, removing unreachable
  or stale interaction paths.

Acceptance criteria:

- the existing release validator still passes;
- the new reader checks fail on missing critical semantics and pass on the
  committed templates or generated site;
- every interactive control has an accessible name and a truthful state;
- content reflows at 320 CSS pixels without loss of prose;
- motion-dependent behavior respects `prefers-reduced-motion`;
- the reader remains usable with JavaScript disabled; and
- no source text, translation, grade, or erratum is changed.

### PR 2 — Passage identity and annotations

Proposed branch: `codex/passage-identity`

Deliverables:

- deterministic English block IDs nested under stable Latin/source-segment
  IDs; finer Latin paragraph IDs only where structure has been verified;
- a generated passage index with chapter, segment, and sequence data;
- passage-based continue-reading state with migration from scroll fractions;
- exact passage links, copy-link, and copy-citation controls;
- structured uncertainty and editorial-note records;
- URL state for work, passage, language/view, and active annotation layers;
- a minimal TEI P5 export for the pilot works; and
- validators for uniqueness, referential integrity, and stable regeneration.

Acceptance criteria:

- rebuilding without content changes produces identical IDs;
- old chapter and segment fragments still resolve;
- a saved reading position survives font-size and viewport changes;
- every displayed note has a source record and addressable target; and
- pilot TEI validates against the selected TEI schema.

### PR 3 — IIIF foundation and facsimile pilot

Proposed branch: `codex/iiif-foundation`

Deliverables:

- add IIIF manifest, API-version, rights, and attribution fields to source
  metadata;
- implement provider discovery for BSB, e-rara, and BnF/Gallica;
- investigate and document HAB, dilibri, and Internet Archive fallbacks;
- normalize provider metadata into generated IIIF Presentation 3 manifests;
- represent chapters as IIIF Ranges and text as Annotation Pages;
- add a Mirador 4 or focused OpenSeadragon source viewer pilot;
- cache only metadata and approved derived thumbnails, not entire books; and
- handle remote failure with a persistent institutional source link.

Pilot works:

- `prdl-24362_de-laude-scriptorum-manualium` — short BSB prose;
- `prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam` — BnF,
  facsimiles, and cipher material; and
- one BSB `Polygraphia` witness — long structured and multi-witness material.

Acceptance criteria:

- manifests and rights statements validate;
- the viewer opens the correct canvas from a passage URL;
- remote API or CORS failure does not remove the readable text;
- source attribution remains visible in full-screen mode; and
- page mappings distinguish exact from approximate alignment.

### PR 4 — Unified study reader

Proposed branch: `codex/study-reader`

Deliverables:

- Read, Study, and Source modes sharing a passage cursor;
- responsive English/Latin/facsimile layouts;
- bidirectional passage and image-region highlighting where coordinates exist;
- accessible note popovers using browser-native primitives with fallback;
- in-work search and a match-density strip;
- chapter minimap and passage-based progress;
- optional normalized/diplomatic and annotation layers; and
- touch, keyboard, screen-reader, print, and reduced-motion behavior.

Acceptance criteria:

- switching mode, theme, width, or viewport does not lose the active passage;
- keyboard focus never disappears behind sticky UI;
- mobile uses an intentional stacked view rather than compressed columns;
- deep links reproduce the selected passage and view; and
- a complete work remains readable when enhancements fail.

### PR 5 — Publication exports

Proposed branch: `codex/publication-exports`

Deliverables:

- one EPUB 3.3 package per publishable reading edition;
- navigation document, landmarks, language metadata, accessibility metadata,
  notes, provenance, and institutional source links;
- `epubcheck` validation in the release process;
- Vivliostyle paged-media styles for print and PDF;
- page-break, table, cipher, note, and image handling; and
- a documented versioning and citation policy for generated editions.

Acceptance criteria:

- EPUBs validate without errors;
- a short, long, and cipher-heavy edition are tested in at least two reading
  systems;
- print output contains no clipped tables or interface chrome; and
- downloadable editions carry the same editorial caveats as the website.

### PR 6 — Executable cipher edition

Proposed branch: `codex/cipher-trace-lab`

Deliverables:

- trace a worked example through cover text, extraction rule, cipher stream,
  substitution table, and recovered plaintext;
- connect each step to the relevant text passage and facsimile region;
- distinguish printed evidence, transcription repair, and inferred operation;
- add keyboard-operable step navigation and non-color status encoding; and
- provide a plain-text explanation and data download for every visual trace.

Acceptance criteria:

- every displayed transformation can be recomputed from committed data;
- unresolved or reconstructed characters remain explicit;
- the visualization has an equivalent tabular/textual form; and
- no animation is required to understand the method.

### PR 7 — Witness comparison pilot

Proposed branch: `codex/witness-comparison-pilot`

Deliverables:

- collate one short, manually verified passage across two or three witnesses;
- preserve diplomatic and normalized comparison layers;
- classify substantive, orthographic, OCR, and unresolved variation;
- visualize alignment as readable columns with restrained connecting ribbons;
- link every reading to its witness and facsimile; and
- export the apparatus as TEI `app/lem/rdg` and plain tabular data.

Acceptance criteria:

- a human verifies the source transcription before variant publication;
- the interface never labels raw OCR disagreement as textual variation;
- every reading remains legible without the connectors; and
- the data can be regenerated deterministically.

### Later research — entity and semantic exploration

Entity indexes, a printer/monastery/place chronology, intertextual references,
and semantic passage discovery should follow only after stable passage targets
exist. Embeddings and clustering remain optional progressive enhancements.
Their models, parameters, and limitations must be shown, and every result must
link to supporting passages.

## 7. Quality fixtures

Every reader-facing PR should exercise at least these cases:

| Fixture | Reason |
| --- | --- |
| `prdl-24362_de-laude-scriptorum-manualium` | Short prose and ordinary reading |
| `prdl-24380_admonitiones-exhortationes-monachos` | Very long text and performance |
| `prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam` | BnF, ciphers, tables, and facsimile |
| `prdl-24390_polygraphiae-libri-vi` | BSB, long structured text, and witness family |
| `prdl-24364_de-laudibus-sanctissimae-matris-annae` | Six-witness family |

Generated T4B reading views are included whenever the feature affects their
continuous-reading presentation.

## 8. Test and review matrix

### Automated source checks

- manifest and metadata schema checks;
- unique IDs and valid fragment references;
- heading and landmark order;
- `lang` coverage for Latin and English;
- button name/state/control relationships;
- internal links, source links, and generated artifact inventory;
- IIIF and TEI validation;
- EPUB validation; and
- deterministic build comparison for generated scholarly data.

### Browser checks

- Chromium, Firefox, and WebKit where the local browser harness permits;
- keyboard-only reading and navigation;
- screen-reader-oriented semantic inspection;
- 320px reflow and 200%/400% zoom;
- light, dark, high-contrast, and forced-colors behavior;
- reduced motion;
- JavaScript disabled;
- print preview; and
- representative slow-network and failed-image states.

### Visual review

Golden screenshots should cover desktop and narrow layouts for one short work,
one very long work, the parallel reader, a Style C page, a cipher tool, and the
search page. Screenshot differences are review evidence rather than an
automatic claim that a design is correct.

## 9. Success measures

The sweep is successful when:

- a reader can cite and return to an exact passage reliably;
- a scholar can reach the supporting print page without manually hunting;
- English, Latin, uncertainty, and source evidence never blur into one layer;
- all ordinary reading works without a server or mandatory JavaScript;
- the major reader paths meet WCAG 2.2 AA expectations;
- EPUB and print editions validate and preserve provenance;
- witness and cipher visualizations are evidence-backed and reproducible; and
- experimental analysis remains visibly distinct from editorial fact.

## 10. Explicit non-goals

- no single-page-application rewrite;
- no server requirement for ordinary reading;
- no skeuomorphic page-turn animation as the default reader;
- no faux-antique body type at the expense of legibility;
- no silent modernization of Latin or concealment of OCR uncertainty;
- no automatic critical edition built from unverified OCR;
- no opaque AI summary or semantic map presented as scholarship; and
- no large dependency adopted solely for a visual effect.

## 11. Research references

- TEI P5 Guidelines: <https://tei-c.org/release/doc/tei-p5-doc/en/html/index.html>
- IIIF Presentation API 3: <https://iiif.io/api/presentation/3.0/>
- IIIF Content Search API 2: <https://iiif.io/api/search/2.0/>
- IIIF Cookbook: <https://iiif.io/api/cookbook/>
- W3C Web Annotation Data Model: <https://www.w3.org/TR/annotation-model/>
- DPUB-ARIA 1.1: <https://www.w3.org/TR/dpub-aria-1.1/>
- WCAG 2.2: <https://www.w3.org/TR/WCAG22/>
- EPUB 3.3: <https://www.w3.org/TR/epub-33/>
- EPUB Accessibility 1.1: <https://www.w3.org/TR/epub-a11y-11/>
- Vivliostyle: <https://vivliostyle.github.io/vivliostyle.js/docs/en/>
- Mirador: <https://github.com/ProjectMirador/mirador/releases>
- CETEIcean: <https://github.com/TEIC/CETEIcean>
- CollateX: <https://collatex.net/doc/>
- LERA: <https://academic.oup.com/dsh/article/38/1/330/6623571>
- DuckDB-Wasm: <https://duckdb.org/docs/stable/clients/wasm/overview>
