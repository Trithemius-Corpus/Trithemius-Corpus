# Publication rebuild and quality checks · 17 November 2026

The reading site can now be reconstructed from a public checkout. The starting
edition was commit `870a6c62c9decad9d86cef63c026adbf3a81bee2`. Its 47
passage indexes supply the historical ID-to-text fingerprints. Its specialized
pages supply the 463 rendered apparatus chunks in ten work files under
`data/publication/apparatus/`. Those files preserve the published English
and the accompanying facsimile references.

| Area | Publication contract |
|---|---|
| Passage identity | A staged build compares each rendered passage with its index and the historical fingerprint. The two Scribes wording changes are explicit migrations. Three compound passages in *Steganographia* retain their cited text across multiple valid HTML blocks. |
| T4B assembly | Numbered chunks are assembled in staging. Dated changes replay against exact before/after digests. Accepted errata and edition metadata travel with the text. The original 19 Scribes chunks reproduce the corrected edition. |
| Citation and provenance | Each of the 27 T4B citations identifies its own reading page and repository folder. The Leipzig Saint Anne witness has an explicit cross-reference between its two historical slugs. |
| Source images | All three IIIF readers check canvas bounds. Seven distinct Scribes passage anchors have reviewed targets. Other targets use an approximate segment mapping or the institutional source. Both the toolbar and the embedded viewer identify reviewed locations. |
| Release workflow | The Pages workflow validates the checked-in directory, uploads it and makes deployment depend on that artifact. A separate CI job exercises reconstruction. These workflow changes were checked locally. |
| Editorial records | Current audit coverage, dated corrections and human review come from shared records. A complete audit requires every chunk. Per-work attribution records distinguish Hucbald as author, Trithemius as transmitter, and the traditional attribution of the *Sigilla*. |
| Research record | The Scribes queue requires its declared source snapshot and all three contextual ledgers. The frozen comparison has 1,728 lexical candidates. The current recomparison has 1,716. The pen modifier is withheld from benchmark use pending philological adjudication. |
| Book exports | Every EPUB has a dated, content-derived revision. A single-work rebuild updates both files and their index row. The validator checks digests and roles against the package and the source record. |
| Discovery | The sitemap enumerates 163 canonical pages. Search indexes English passages, Latin OCR segments and editorial notes using a single field. The parallel glossary uses the 161 editorial entries and 36 technical entries, including registered inflections. |

## Local checks

```console
python scripts/build_manifest.py
python scripts/build_editorial_ledger.py --check
python scripts/build_translation_disagreements.py --check
python scripts/build_site.py
python scripts/build_publication_exports.py
python scripts/build_search.py
python -m unittest discover -s tests
python scripts/check_publication.py
```

Use `python scripts/run_epubcheck.py site/dist/editions/epub/*.epub` on a shell
that expands globs. In PowerShell pass `(Get-ChildItem site/dist/editions/epub/*.epub).FullName`.
The official EPUBCheck 5.3.0 run checked all 47 packages. Their recorded SHA-256
digests identify the checked files, which returned zero errors and zero warnings.

All 42 regression tests and all 13 publication validators passed. A separate
checkout of the staged Git files successfully rebuilt Scribes, then the full
site and all book exports. All 220 compared reader, interchange and discovery
files matched in text content. All 47 EPUBs and all 47 print editions matched
their checked-in SHA-256 digests. A fresh Pagefind build in that checkout
verified 63,806 passage and note targets. The release validator also reported
the README’s existing placeholder for a future Zenodo DOI.

In the local in-app browser, searching *salubrius* opened Scribes Latin segment
3. Enter on *scriptoris* opened the glossary entry for *scriptor*. Opening Source
from the abilities passage retained folio 2r, canvas 5. Moving the viewer back
to canvas 8 selected the pen passage, `p-en-0003-0001`.

The separate [translation review](translation-quality-2026-11-17.md) gives
the quotations, witness links and six print-supported correction priorities
found outside the Scribes implementation.
