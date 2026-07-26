# Passage identity and annotation model

Status: implementation profile for `passage-index-v1`

This profile gives every addressable English block in a standard corpus work a
durable identity below the chapter level. It is deliberately narrower than a
critical-edition apparatus. In particular, it does not claim paragraph-level
alignment for Latin OCR whose only defensible correspondence is the translation
segment from which the English was produced.

## Identifier invariants

A source segment has a canonical identifier of the form:

```text
trc:{work_id}:seg-{segment:04d}
```

An English passage nested within it has:

```text
trc:{work_id}:seg-{segment:04d}:p-{sequence:04d}
```

Its HTML fragment is shorter but carries the same components:

```text
p-en-{segment:04d}-{sequence:04d}
```

These identifiers depend only on the work ID, the source segment number, and
the passage's order among rendered addressable blocks in that segment. They do
not depend on viewport dimensions, fonts, line wrapping, page height, a model
name, or a build timestamp.

Existing chapter and segment anchors remain in place. When an existing heading
already owns an `id`, the builder adds an adjacent stable passage anchor instead
of replacing the older fragment.

## Addressable blocks

Version 1 addresses non-nested rendered blocks with meaningful text:

- paragraphs and headings;
- lists as a whole rather than unstable individual list items;
- tables as a whole rather than cells reconstructed from damaged OCR;
- block quotations; and
- preformatted source or cipher material.

Build-only `PASSAGE-SEG` comments retain chunk provenance through Markdown
rendering. They are removed before publication. The resulting document remains
ordinary static HTML and all passage fragments work without JavaScript.

## Passage index

Each standard work build writes:

```text
site/dist/data/passages/{work_id}.json
```

The JSON conforms to
[`data/schemas/passage-index.schema.json`](../data/schemas/passage-index.schema.json)
and contains:

- immutable work and witness identifiers;
- source segments with Latin OCR and source-page mappings;
- English passage text, kind, chapter membership, and public targets;
- an explicit `alignment_precision: "segment"` statement;
- structured editorial annotations; and
- a deterministic SHA-256 content digest.

The digest covers the artifact before the digest field is added. No volatile
generation date is written, so two builds from the same inputs are byte-for-byte
identical.

## Annotation profile

The first structured layer covers visible inline editorial markers such as
`[unclear]`, `[sic]`, `[ed.]`, `[note]`, and OCR/translation notes. The marker
remains visible in prose and receives a stable HTML target. Its JSON record uses
the W3C Web Annotation shape:

- `type: "Annotation"`;
- a textual body with a controlled tag;
- `motivation: "describing"`; and
- a fragment selector pointing to the visible marker.

The schema is
[`data/schemas/annotation.schema.json`](../data/schemas/annotation.schema.json).
Footnotes, errata files, named entities, and witness variants will become
additional annotation bodies only when their source and targeting semantics are
equally explicit.

## Reader URL and progress state

Passage links use the stable fragment plus explicit reader state:

```text
works/{work_id}.html?view=read&lang=en&annotations=visible#p-en-0001-0001
```

The current reader has one implemented view and language; writing those values
now keeps links forward-compatible with the later Study and Source readers.
Unknown query parameters do not affect static reading.

Continue-reading records use local-storage version 2 and retain the former
scroll fraction only as a fallback. New records store the nearest passage ID.
An older fraction-only entry produces a one-time `?resume=` link; after the page
opens, the reader removes that temporary parameter and records the nearest
stable passage. No automatic migration rewrites unrelated browser storage.

## TEI P5 pilot

The build exports three representative works:

- `prdl-24362_de-laude-scriptorum-manualium` — short ordinary prose;
- `prdl-24390_polygraphiae-libri-vi` — long structured cipher material; and
- `prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam` — complex
  cryptographic prose and editorial uncertainty.

Each export contains a Latin source-segment text, an English translation text,
`corresp` links at the declared segment precision, and stand-off annotation
notes. The constrained profile is validated with
[`data/schemas/trithemius-pilot.rng`](../data/schemas/trithemius-pilot.rng).
It is a pilot interchange format, not a claim that the underlying OCR is a
critical transcription.

## Compatibility and change policy

- `passage-index-v1` IDs must not be renumbered for typography or template
  changes.
- A content edit that splits, joins, inserts, or removes an addressable block
  may change later passage sequence numbers within that source segment. Such a
  release must publish a redirect map before replacing old fragments.
- Model or editorial-layer changes require a new `transform_version`, not a new
  work or witness identity.
- Latin alignment finer than a source segment requires human verification and
  a new precision value; it must never be inferred silently from paragraph
  order.
