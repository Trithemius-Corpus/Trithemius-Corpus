# Contributing

This corpus is machine-produced. Human correction is the main way it gets better. Before contributing, read the limitations section in [METHODOLOGY.md](METHODOLOGY.md#11-limitations-known-failure-modes): it describes the known failure modes and tells you where corrections are most needed.

## What helps

Three kinds of contribution are especially useful.

### 1. Translation errata

A note that a specific English rendering is wrong, checked against the Latin. To be actionable, a report needs:

- the work id — the directory name under `works/` (the `prdl-NNNNN` prefix is enough);
- the chunk file — `works/<id>/chunks/full_chunk_NNNN.md`;
- the current English wording at issue;
- the Latin it should answer to, from `works/<id>/latin-ocr.txt` or from the side-by-side viewer on the project site;
- a suggested correction, and how confident you are in it.

Use the **Translation erratum** issue template. Mistranslation, omission, and invented content are all in scope. So are leftover preamble artifacts ("Here is the translation:") described in the methodology.

### 2. OCR corrections

The Latin in `latin-ocr.txt` is OCR output, and OCR damage is itself a frequent cause of translation error. If the OCR misreads the print, report it against the source scan, not against your expectation of what the Latin ought to say. Cite the page. The parallel viewer and, for the cryptographic works, the facsimile pages show the source page images; each work's `metadata.json` records the holding institution and edition, so the scan can be checked independently.

A useful report gives the work id, the page, the current OCR reading, and the correct reading per the scan. Use the **OCR error** issue template.

### 3. Domain-terminology notes

Trithemius writes in monastic, liturgical, hagiographic, and cryptographic registers, each with technical vocabulary a model can flatten. A note such as "in this monastic-rule context, *conversio* is a technical term and should be rendered *conversion of life*, not *conversion*" is valuable even without a full corrected passage. A note that applies across many chunks or works is more valuable still; say so if you believe it does. Open a free-form issue for these.

Out of scope: collation of variant readings between editions. This corpus translates one OCR witness per work and is not a critical edition; see the scope notes in [METHODOLOGY.md](METHODOLOGY.md#12-what-this-corpus-is-good-for-and-what-it-is-not).

## How corrections are recorded

The machine output in `english.md` is not silently overwritten. This is deliberate: the corpus documents what the pipeline produced, and the audit grades in `chunks/grades.csv` refer to that text. Corrections are instead tracked in a per-work erratum file, `works/<id>/ERRATA.md`, so the provenance of every human edit stays clear.

An erratum entry records the chunk, the original rendering, the corrected rendering, the Latin basis, the contributor, and the date. When a correction is accepted, the maintainer adds the entry and, where warranted, applies the fix to the published text — with the erratum file as the record of who changed what, and why.

If you open a pull request rather than an issue, add your correction to `works/<id>/ERRATA.md` (create the file if it does not exist) instead of editing `english.md` or the chunk files directly. Pull requests that rewrite the machine output in place, without an erratum entry, will be asked to restructure.

## Do not edit `site/dist/`

`site/dist/` is build output. It is committed because CI cannot rebuild it: `scripts/build_site.py` needs the working corpus, which is intentionally not in this repository. The maintainer rebuilds the site locally after content changes. Pull requests should not hand-edit anything under `site/dist/`; change the source files, and the site will be regenerated to match.

## Reader changes

Reader-facing changes must preserve semantic HTML, fragment targets, narrow
reflow, and the representative short, long, cipher, and multi-witness pages in
`data/reader_fixtures.json`.

Run the dependency-free publication checks against the committed site:

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

The repository is licensed [CC BY 4.0](LICENSE). By contributing, you agree that your contribution is published under the same license. Accepted corrections are credited by name in the erratum entry; if you prefer a different attribution, or none, say so in the issue or pull request.
