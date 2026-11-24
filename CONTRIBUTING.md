# Contributing

This corpus is machine-produced. Human correction is the main way it gets better. Before contributing, read the limitations section in [METHODOLOGY.md](METHODOLOGY.md#11-limitations-known-failure-modes): it describes the known failure modes and tells you where corrections are most needed.

## What helps

Three kinds of contribution are especially useful.

### 1. Translation errata

A note that a specific English rendering is wrong, checked against the Latin. To be actionable, a report needs:

- the catalogue ID and track, either standard (`works/<id>/`) or Trithemius 4B (`works-t4b/<id>/`);
- the passage link or numbered chunk file in that track;
- the current English wording at issue;
- the Latin in that track’s `latin-ocr.txt`, the source image and its printed page or folio when available;
- a suggested correction, and how confident you are in it.

Use the **Translation erratum** issue template. Mistranslation, omission, and invented content are all in scope. So are leftover preamble artifacts ("Here is the translation:") described in the methodology.

### 2. OCR corrections

The Latin in `latin-ocr.txt` is OCR output. Check a suspected error against the printed page and cite its folio or page number. The standard parallel viewer shows the OCR beside the English. Use the institution linked in the edition’s `metadata.json` to find the scan. The study reader and selected apparatus pages also show facsimiles where available.

A useful report gives the work id, the page, the current OCR reading, and the correct reading per the scan. Use the **OCR error** issue template.

### 3. Domain-terminology notes

Trithemius writes in monastic, liturgical, hagiographic, and cryptographic registers, each with technical vocabulary a model can flatten. A note such as "in this monastic-rule context, *conversio* is a technical term and should be rendered *conversion of life*, not *conversion*" is valuable even without a full corrected passage. A note that applies across many chunks or works is more valuable still; say so if you believe it does. Open a free-form issue for these.

Out of scope: collation of variant readings between editions. This corpus translates one OCR witness per work and is not a critical edition; see the scope notes in [METHODOLOGY.md](METHODOLOGY.md#12-what-this-corpus-is-good-for-and-what-it-is-not).

## How corrections are recorded

Each edition has its own correction history. Use `works/<id>/ERRATA.md` for the standard translation and `works-t4b/<id>/ERRATA.md` for the alternate translation. The two tracks may divide the source into different chunks. When two catalogue IDs share a scan, check the other record for the same wording and report its passage separately. Historical grades describe the version that received them.

An erratum entry records the chunk, the original rendering, the corrected rendering, the Latin basis, the contributor, and the date. When a correction is accepted, the maintainer adds the entry and, where warranted, applies the fix to the published text — with the erratum file as the record of who changed what, and why.

For a correction pull request, add an entry to the affected track’s `ERRATA.md` (create it if needed). The maintainer can then apply the accepted wording to the chunk and assembled edition with a dated record of the change.

## Do not edit `site/dist/`

Edit the canonical files and rebuild the reading site from the public checkout. Keep the committed `site/dist/static/images/` tree in place. It includes facsimile WebPs that exist only there, and the staged site build carries them forward. If you need a clean rebuild, use a fresh checkout so those image inputs are present. Install the requirements and follow the site, book and search commands in the [release checklist](docs/RELEASE_CHECKLIST.md).

## Reader changes

Reader-facing changes must preserve semantic HTML, fragment targets, narrow
reflow, and the representative short, long, cipher, and multi-witness pages in
`data/reader_fixtures.json`.

Run the reader and passage checks against the committed site:

```console
python scripts/validate_reader.py
python scripts/validate_passages.py --source-only
```

When Chrome or Chromium is installed, run the representative desktop and
mobile layout audit as well:

```console
python scripts/audit_layout.py --all-fixtures
python scripts/audit_layout.py --all-fixtures --mobile
```

Set `TRITHEMIUS_SITE_DIST` to audit a clean build in another directory before
replacing the committed release output. The browser executable can be selected
with `TRITHEMIUS_CHROME` when it is not in a standard location.

Changes that split, merge, insert, or remove rendered blocks inside a source
segment can change passage fragments. Review
[`docs/PASSAGE_MODEL.md`](docs/PASSAGE_MODEL.md) before making such a change;
published passage IDs require a redirect map when their sequence changes.

## Issues or pull requests

Either is fine. An issue with a precise citation is just as useful as a pull request, and lower friction for a single correction. For corrections across many chunks, a pull request against the relevant `ERRATA.md` files is easier to review. Free-form issues are open for anything the templates do not fit.

## Licensing

Indicate how your correction should be credited. The project publishes its documentation, code and arrangement under CC BY 4.0, and its generated translation text under CC0 1.0. Identify any separately licensed material you supply. For a scan or crop, give the holding institution, source and rights URLs, and describe the crop. The Trier *Sigilla* evidence carries CC BY-NC-SA 3.0. The BSB Mainz comparison leaf for PRDL 24373 carries No Copyright – Non-Commercial Use Only. Keep those terms and credits with copies of the images. [Project license and institutional credits](LICENSE)
