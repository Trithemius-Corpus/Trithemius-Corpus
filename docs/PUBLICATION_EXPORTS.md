# Publication exports

The Trithemius Corpus publishes each of its 47 readable source editions in
three forms drawn from the same canonical `works/<id>/english.md` source:

- the progressively enhanced web reader;
- a deterministic, reflowable EPUB 3.3 reading edition; and
- a semantic HTML edition styled for CSS Paged Media and Vivliostyle PDF.

These are reading editions, not critical editions. Every format repeats the
same warning that machine-assisted English may contain translation error, OCR
damage, and unresolved readings. Institutional source links, methodology,
errata, license, and canonical web URLs travel with each downloadable edition.

## Build and validation

```text
python scripts/build_publication_exports.py
python scripts/validate_publication_exports.py
python scripts/run_epubcheck.py <one-or-more .epub files>
npx @vivliostyle/cli build -d -s A5 -o output.pdf site/dist/editions/print/<work-id>/index.html
```

`build_publication_exports.py` writes fixed ZIP timestamps and a stable member
order. By default it takes the edition version and modification date from
`CITATION.cff`; release automation may override them with
`TRITHEMIUS_EDITION_VERSION` and `SOURCE_DATE_EPOCH`. `run_epubcheck.py`
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

An export inherits the public corpus version. If `CITATION.cff` has no explicit
`version`, its ISO `date-released` is the edition version. A tagged release
should set an explicit semantic version and DOI in `CITATION.cff`; rebuild the
exports after either changes.

For a whole book, cite the author, translated title, source-edition statement,
Ian Carlos Fabin as English editor/translator, *Trithemius Corpus*, version,
format, canonical work URL, and DOI when assigned. For scholarly quotation,
prefer the web or TEI form where stable passage identifiers exist and append
the passage ID. Example:

> Johannes Trithemius, *On the Praise of Scribes*, English ed. Ian Carlos
> Fabin, *Trithemius Corpus*, version 2026-07-12, EPUB 3.3,
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
