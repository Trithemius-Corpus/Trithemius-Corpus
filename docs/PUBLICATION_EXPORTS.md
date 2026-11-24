# Publication exports

The Trithemius Corpus publishes each of its 47 standard catalogue records in
three forms drawn from the same canonical `works/<id>/english.md` source:

- the progressively enhanced web reader;
- a deterministic, reflowable EPUB 3.3 reading edition; and
- a semantic HTML edition styled for CSS Paged Media and Vivliostyle PDF.

These are reading editions, not critical editions. Every format repeats the
same warning that machine-assisted English may contain translation error, OCR
damage, and unresolved readings. Institutional source links, methodology,
errata, license, and canonical web URLs travel with each downloadable edition.
Two pairs of records share a source scan. Each book keeps its catalogue ID and
the relevant headnote identifies its companion record.

## Build and validation

```text
python scripts/build_publication_exports.py
python scripts/validate_publication_exports.py
python scripts/run_epubcheck.py <one-or-more .epub files>
npx @vivliostyle/cli build -d -s A5 -o output.pdf site/dist/editions/print/<work-id>/index.html
```

`build_publication_exports.py` writes fixed ZIP timestamps, platform metadata
and member order. To rebuild one work, pass `--work <id>` to the builder and
validator. The builder stages the EPUB, print files and index together, and
checks their recorded digests before replacing the previous editions directory.
When upgrading a version-1 index, a single-work build retains the other packages
and marks them as legacy. Build the other works to validate a complete release.
`run_epubcheck.py`
downloads the official EPUBCheck 5.3.0 distribution and verifies its pinned
SHA-256 digest before execution.

PDF files are release artifacts rather than repository sources and remain
ignored by Git. The committed paged HTML and CSS are the reproducible input.
The print stylesheet uses a 6 x 9 inch page by default; a release can request a
different trim size through Vivliostyle. Tables use repeating headers,
break-avoidance, fixed print layout, and wrapping so cipher material remains
inside the page box. Interactive website controls and facsimile iframes are
not present in the print source.

## Versioning and citation

Each work has its own revision. Its identifier includes the modification date
and the first 16 hexadecimal digits of a SHA-256 digest of its unversioned
EPUB and print content. The index stores the full content digest and separate
digests for the canonical inputs, EPUB file, print HTML and print CSS.

The most recent dated erratum, AI correction, optional work metadata field
`publication_modified`, or entry in `data/publication/export-history.json`
sets the earliest modification date. When newly edited content has no later
dated entry, its first export records the UTC build date in the index. Rebuilds
of the recorded content retain that date. To reproduce a previously unrecorded
revision from an empty output directory, supply its date in the work metadata
or set `SOURCE_DATE_EPOCH` to the intended UTC modification time.
An explicit `version` in `CITATION.cff` supplies a release label.
`TRITHEMIUS_EDITION_VERSION` overrides that label.

For a whole book, cite the author, translated title, source-edition statement,
Ian Carlos Fabin as English editor/translator, *Trithemius Corpus*, version,
format, canonical work URL, and DOI when assigned. For scholarly quotation,
prefer the web or TEI form where stable passage identifiers exist and append
the passage ID. Example:

> Johannes Trithemius, *On the Praise of Scribes*, English ed. Ian Carlos
> Fabin, *Trithemius Corpus*, [edition version from the EPUB colophon], EPUB 3.3,
> `prdl-24362_de-laude-scriptorum-manualium`.

The repository commit and the SHA-256 values in `site/dist/editions/index.json`
identify the exact generated files. A rebuilt development artifact should not
be described as the same edition if its canonical text or editorial metadata
has changed.

## Reading-system acceptance

Before tagging a release, test the shortest edition, the longest edition, and
the table-heavy *Polygraphiae libri VI* in at least two current EPUB reading
systems. Record application names and versions in the release notes. Check the
table of contents and landmarks, font enlargement, dark/light reader themes,
search, external institutional links, cipher-row reflow, and the final
provenance page. EPUBCheck is a conformance checker, not a substitute for this
human reading-system pass.

The July 2026 implementation audit additionally rendered the short *Ecloga de
Laude Calvorum*, the 2,379-page *Chronicon Hirsaugiense & Sponheimense*, and
the 323-page cipher-heavy *Polygraphiae libri VI* with Vivliostyle CLI 11.1.0.
First, middle, dense-cipher, and final pages showed no clipped content or web
interface chrome.

In the print colophon, the canonical link spells out its own address once. Links with descriptive labels, including the institutional source, still print their destinations.

On 23 November 2026, local checks used *In Praise of Scribes* (24362), *On Ecclesiastical Writers* (70287) and *Key to the Polygraphia* (70282). A numeric example in the *Key* ran off the edge of the print page and a narrow EPUB screen. Paged HTML can now wrap uninterrupted strings. The EPUB groups the 287 numbers at existing colons so readers can wrap all 1,062 characters while preserving the source sequence. Tables with six or more columns use compact EPUB styling. The narrow-screen check includes the rightmost value 900 in the *Key*. [Audit, samples and verification](tasks/pre-push-review-2026-11-23.md)
