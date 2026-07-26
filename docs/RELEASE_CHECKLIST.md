# Release checklist

Use this checklist for a public release. The committed repository is the release
corpus and `site/dist/` is deployed as-is; CI does not have the private working
corpus needed to regenerate every artifact from scans.

## 0. Pre-push sanity

- [ ] `python scripts/validate_release.py` - confirm manifest/work metadata, quality ledgers, docs, links, search assets, and junk-file checks pass.
- [ ] `python -c "import py_compile, glob; [py_compile.compile(f, doraise=True) for f in glob.glob('scripts/*.py')]"` - confirm all public scripts parse (the glob is expanded by Python, so this works in PowerShell and bash alike; `python -m py_compile scripts/*.py` only works where the shell expands the wildcard).
- [ ] `python scripts/build_site.py` - rebuild static pages from committed release artifacts and available local working-corpus extras.
- [ ] `python scripts/validate_cipher_trace.py` - recompute the executable Modus II trace and verify its evidence labels, accessible controls, text equivalent, and downloads.
- [ ] `npx pagefind --site site/dist` - rebuild search after the static site changes.
- [ ] `python scripts/build_publication_exports.py` - rebuild all EPUB 3.3 and paged-HTML reading editions.
- [ ] `python scripts/validate_publication_exports.py` - confirm package structure, metadata, provenance, caveats, and print contracts.
- [ ] `python scripts/run_epubcheck.py site/dist/editions/epub/*.epub` - validate every EPUB with pinned official EPUBCheck 5.3.0 (PowerShell: pass `(Get-ChildItem site/dist/editions/epub/*.epub).FullName`).
- [ ] Render a short, long, and cipher-heavy print edition with `npx @vivliostyle/cli build -d -s A5 -o output.pdf site/dist/editions/print/<work-id>/index.html`; visually inspect first, middle, table, and final pages.
- [ ] Open the same short, long, and cipher-heavy EPUBs in two current reading systems (recommended: Thorium Reader and Calibre), checking navigation, reflow, tables, links, and large-text behavior.
- [ ] Open `site/dist/index.html`, `site/dist/works.html`, `site/dist/scoreboard.html`, `site/dist/search.html`, one representative work page, one parallel viewer, one Style C page, and `site/dist/cipher-solutions.html`.
- [ ] Confirm the release quality claim is `S=47 / A=0 / B=0 / C=0 / F=0`, 4,400 published chunks, 4,353 graded chunks, 4.63/5 mean faithfulness, and 0.0% confirmed hallucination.
- [ ] Confirm `git status --short` contains only intentional release changes.

## 1. Push

- [ ] `git push -u origin main`
- [ ] GitHub -> repo **Settings -> Pages -> Source = GitHub Actions** (one time)
- [ ] Confirm the `Deploy site to GitHub Pages` workflow runs green; visit `https://trithemius-corpus.github.io/Trithemius-Corpus/`

## 2. Tag a release

- [ ] `git tag -a v1.0 -m "Trithemius Corpus v1.0 - 47 works, all S-tier, 4,400 chunks, 0% confirmed hallucination"`
- [ ] `git push origin v1.0`
- [ ] Create the GitHub Release from the tag.

## 3. Zenodo DOI

- [ ] Link the GitHub repo in Zenodo before creating the release, or use "Create new version" if already linked.
- [ ] Zenodo ingests the tag and reads `.zenodo.json`.
- [ ] Paste the concept DOI back into `CITATION.cff`, `README.md`, and `.zenodo.json`, then commit "Add Zenodo DOI" and push.

## 4. Internet Archive mirror (optional)

- [ ] Preferred: upload a `.zip` snapshot of `site/dist/` plus `manifest.json` as a dataset item, cross-linked to the Zenodo DOI.
- [ ] Alternative: register the GitHub Pages URL with the Wayback Machine.

## 5. Post-release

- [ ] Flip README Phase 4 to `[x]`.
- [ ] Optional Phase 5: methodology paper.

## Rebuild dependency note

`site/dist/` is committed and deployed verbatim. Normal work pages rebuild from
the release artifacts under `works/`; some optional facsimile and Style C
assets still require `TRITHEMIUS_WORKING` (set to your private corpus root).
If you change translations, intros, metadata, titles,
templates, or static assets, rebuild locally and commit both the source
artifact and `site/dist/`.
