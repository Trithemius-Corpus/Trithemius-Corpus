# Release checklist

Use this checklist for a public release. The committed repository is the release
corpus and `site/dist/` is deployed as-is; CI does not have the private working
corpus needed to regenerate every artifact from scans.

## 0. Pre-push sanity

- [ ] `python scripts/validate_release.py` - check catalogue records and shared sources, quality ledgers, docs, links, search assets and the citation file. The CFF 1.2.0 check uses the pinned official schema shipped in `data/schemas/` and runs offline.
- [ ] `python -c "import py_compile, glob; [py_compile.compile(f, doraise=True) for f in glob.glob('scripts/*.py')]"` - confirm all public scripts parse (the glob is expanded by Python, so this works in PowerShell and bash alike; `python -m py_compile scripts/*.py` only works where the shell expands the wildcard).
- [ ] `python scripts/build_site.py` builds both reading tracks, the specialized pages and the final sitemap in a staging directory. It checks published passage identities before swapping in the result.
- [ ] `python scripts/validate_cipher_trace.py` - recompute the executable Modus II trace and verify its evidence labels, accessible controls, text equivalent, and downloads.
- [ ] Run `python scripts/build_search.py` after building the site. It indexes the finished pages with Pagefind 1.5.2 and verifies each published search target before replacing the bundle.
- [ ] `python scripts/build_publication_exports.py` - rebuild all EPUB 3.3 and paged-HTML reading editions.
- [ ] `python scripts/validate_publication_exports.py` - confirm package structure, metadata, provenance, caveats, and print contracts.
- [ ] `python scripts/run_epubcheck.py site/dist/editions/epub/*.epub` - validate every EPUB with pinned official EPUBCheck 5.3.0 (PowerShell: pass `(Get-ChildItem site/dist/editions/epub/*.epub).FullName`).
- [ ] Render a short, long, and cipher-heavy print edition with `npx @vivliostyle/cli build -d -s A5 -o output.pdf site/dist/editions/print/<work-id>/index.html`; visually inspect first, middle, table, and final pages. Omit `-s A5` to check the native 6 × 9 inch layout. In the *Key to the Polygraphia* (PRDL 70282), verify the long colon-separated numeric example through its final `:299:300:301` and compare each column of the table with the source.
- [ ] Open the same short, long, and cipher-heavy EPUBs in two current reading systems (recommended: Thorium Reader and Calibre), checking navigation, reflow, tables, links, and large-text behavior. At narrow widths and enlarged type, check that the *Key* still shows 900 in the sixth column and that all numeric groups remain available.
- [ ] Open `site/dist/index.html`, `site/dist/works.html`, `site/dist/scoreboard.html`, `site/dist/search.html`, one representative work page, one parallel viewer, one Style C page, and `site/dist/cipher-solutions.html`.
- [ ] Run `python scripts/build_editorial_ledger.py --check` and compare catalogue coverage, corrections, and human review status with the intended release.
- [ ] Run `python scripts/check_publication.py` against the completed publication and `python -m unittest discover -s tests` for the regression suite.
- [ ] Confirm `git status --short` contains only intentional release changes.

## 1. Review and publish the site

- [ ] When the changes are ready for remote review, open a pull request from the topic branch. For a dependent PR, compare against the preceding topic branch until its changes land on `main`.
- [ ] Review the intended diff and its checks before merging. Under the Pages workflow, a merge into `main` that changes `site/dist/**` or `.github/workflows/pages.yml` triggers deployment.
- [ ] For a site release, confirm that Pages uses GitHub Actions and that the deployment completed. Open the published reader and check a changed edition. [Pages workflow](../.github/workflows/pages.yml) · [Published reader](https://trithemius-corpus.github.io/Trithemius-Corpus/)

## 2. Tag a release

- [ ] Describe the printed witnesses, revision, and documented review scope in the release tag.
- [ ] `git push origin v1.0`
- [ ] Create the GitHub Release from the tag.

## 3. Zenodo DOI

- [ ] Link the GitHub repo in Zenodo before creating the release, or use "Create new version" if already linked.
- [ ] Zenodo ingests the tag and reads `.zenodo.json`.
- [ ] Paste the concept DOI back into `CITATION.cff`, `README.md`, and `.zenodo.json`, then commit "Add Zenodo DOI" and push.

## 4. Internet Archive mirror (optional)

- [ ] For a site archive, include `site/dist/`, `manifest.json` and `LICENSE`. Any archive that includes correction images must carry their `facsimiles/images.json` and `crops.json` records with the images. Preserve the institutional credits and rights URLs for Trier’s *Sigilla* and the Mainz comparison leaf. Link the archive to the Zenodo DOI when assigned.
- [ ] Alternative: register the GitHub Pages URL with the Wayback Machine.

## 5. Post-release

- [ ] Check that the README citation and distribution links resolve for the released version.
- [ ] Optional Phase 5: methodology paper.

## Rebuild dependency note

`site/dist/` is committed and deployed verbatim after validation. Normal pages
rebuild from `works/`, `works-t4b/`, and the public apparatus and page
mappings in `data/publication/`. The private working corpus is only needed
to repeat the original OCR, translation, or extraction of new apparatus.
The committed `site/dist/static/images/` tree supplies facsimile WebPs that
have no second copy under `site/static/`. Build from a fresh checkout or keep
this image tree when preparing the staged site.
If you change translations, intros, metadata, titles,
templates, or static assets, rebuild locally and commit both the source
artifact and `site/dist/`.
