# Trithemius Corpus: Site-Wide Editorial Rework Plan

## Purpose

Rebuild the public corpus as a professional scholarly working edition rather
than a pipeline dashboard. The site must make a clear distinction between what
the source says, what a machine produced, what automated checks suggest, what a
human has reviewed, and what is ready for uninterrupted reading.

This program covers every public work and edition: the earlier translation
track, Trithemius 4B, parallel viewers, source-witness pages, cipher and table
renderings, indexes, methodology, search, and corpus-level statistics.

## Governing principles

1. **No machine output is presented as human certification.**
2. **Reading text and archival witness are separate views.** Page markers,
   running heads, catchwords, scan stamps, and production chunks remain in the
   archival record but not in ordinary reading flow.
3. **Evidence is shown directly.** Review coverage, known defects, source
   condition, and provenance replace prestige-oriented badges.
4. **Meaningful structure is preserved.** Tables, alphabets, sigils, verse,
   prayers, refrains, marginalia, and uncertain readings are never flattened by
   generic prose cleanup.
5. **Nothing becomes “recommended” merely because it scored well.** A default
   reading view may be identified, but the reason must be stated precisely.
6. **A release is a reviewed artifact, not merely a successful build.**

## 1. Replace the grading model

### Public presentation

Retire the public `S/A/B/C/F` tier badge and the phrases “top tier,” “all-S,”
and similar claims. In particular, `S` must not be used for a machine
translation. Historical machine grades remain available in provenance data and
methodology records, but are labeled **automated QA signals**.

Each work page should instead show four independent fields:

| Field | Examples | Meaning |
|---|---|---|
| Text origin | Machine translation; Human translation | Who produced the prose |
| Human review | None; Partial; Complete | Direct comparison against a source witness |
| Editorial state | Draft; Reading text prepared; Diplomatic only | Whether page furniture and structure have been edited |
| Automated QA | Not run; Sampled; Full machine audit | Scope of automated comparison, never certification |

### Internal triage grade

Keep a non-public triage grade for prioritizing work:

- **A — human-verified:** complete human comparison against the cited witness.
- **B — reviewed working text:** substantial human comparison plus complete
  structural and automated checks.
- **C — provisional machine translation:** readable but not human-verified, or
  known to contain editorial/OCR/translation defects.
- **D — diplomatic or damaged:** incomplete, structurally unsafe, badly damaged,
  or unsuitable for continuous reading.

Under this definition, the current machine-translated corpus begins at **C**
unless human review evidence supports promotion. No bulk promotion is allowed.

### Migration requirements

- Preserve historical grades in machine-readable audit files.
- Remove grade-driven colors, sorting, claims, and hero statistics from the
  public site.
- Replace `tier` in templates with the four evidence fields above.
- Rewrite introductions that say “top tier (S).”
- Rewrite README, Methodology, Scoreboard, work index, genre pages, and metadata
  explanations together so no contradictory claims remain.

## 2. Establish the editorial view model

Every work must be assigned one or more explicit views:

### Clean reading view

- Continuous prose with real paragraphs and semantic headings.
- No running heads, folio numbers, catchwords, signatures, scan stamps, blank
  leaves, production segment gaps, or duplicated scan sequences.
- Page boundaries retained as unobtrusive anchors when reliable.
- Editorial interventions documented and reproducible.

### Diplomatic translation view

- Page and segment divisions preserved.
- OCR uncertainty and damaged leaves visible.
- Suitable for auditing the translation against the scan.

### Parallel witness view

- Latin/OCR and English aligned by stable page or segment identifier.
- Clear warnings where alignment is uncertain or one side is missing.
- Facsimile link available at the relevant location when possible.

### Structured/special view

- Required for cipher alphabets, numeric tables, sigils, diagrams, recipes,
  verse, litanies, and other non-prose material.
- Page position and table alignment preserved whenever they carry meaning.

No single generic renderer should be forced on all four cases.

## 3. Site-wide content audit

Create a machine-readable editorial ledger with one row per public edition and
the following minimum fields:

- work and edition identifiers;
- source provider, date, and witness;
- translation origin and model/version;
- human-review status and reviewer evidence;
- automated-audit scope;
- reading-view status;
- running-head and catchword status;
- paragraph and heading status;
- page/segment continuity status;
- tables, cipher material, verse, images, and marginalia flags;
- known OCR damage, untranslated passages, truncations, and duplicated scans;
- release disposition and blocking issues.

Audit both `works/` and `works-t4b/`. The existing T4B cleanup is a pilot, not
the completion criterion for the site.

## 4. Visual and information-architecture facelift

### Visual direction

- Reduce decorative “occult dashboard” styling in favor of restrained book and
  library typography.
- Use a light-first reading surface with an optional dark theme.
- Limit accent colors to navigation and annotations; do not color-code quality
  as prestige.
- Establish consistent type sizes, measure, leading, paragraph rhythm, heading
  hierarchy, tables, quotations, notes, and captions.
- Treat title pages, verse, lists, recipes, and tables as distinct typographic
  forms.

### Page hierarchy

1. Bibliographic identity and concise title.
2. Plain-language status notice: machine translated, review state, known risks.
3. View selector: Read / Compare / Diplomatic / Facsimile where available.
4. Brief scholarly introduction.
5. Text.
6. Citation, provenance, corrections, and technical audit details.

### Corpus navigation

- Replace grade-first browsing with title, date, genre, language/view status,
  and human-review filters.
- Distinguish works from editions clearly.
- Merge duplicate entry points where they confuse readers.
- Provide a coherent table of contents and persistent reading progress.
- Make search results identify the edition and view being searched.

### Accessibility and responsive requirements

- WCAG-conscious contrast and keyboard navigation.
- Semantic headings and landmarks.
- Responsive tables with captions and non-visual descriptions.
- Reader controls that do not hide core content or override user preferences.
- Print styles suitable for a clean reading copy.

## 5. Implementation phases

### Phase 0 — Freeze claims and establish baseline

- Stop publishing “all-S” and “recommended because of grade” claims.
- Capture screenshots and structural metrics for every page type.
- Record the current public build as the comparison baseline.

**Gate:** every public quality claim has an identified evidence source.

### Phase 1 — Evidence and metadata migration

- Add the four public evidence fields and internal triage grade.
- Generate the editorial ledger.
- Update templates and indexes to consume the new fields.
- Rewrite public methodology and README language.

**Gate:** no public page implies human review where none occurred; no `S` badge
or “all-S” claim remains.

### Phase 2 — Whole-corpus structural audit

- Audit both edition roots and every generated view.
- Detect running heads, page furniture, catchwords, broken words, truncated
  sentences, duplicate pages, empty leaves, OCR notices, and false headings.
- Classify each defect as safe automatic cleanup, work-specific editorial work,
  or human review required.

**Gate:** every edition has a disposition in the editorial ledger.

### Phase 3 — Reading-edition production

- Apply continuous-reading transforms to ordinary prose.
- Hand-configure sermons, verse, prayers, lists, and title matter.
- Preserve cipher/table/sigil works in structured views pending manual review.
- Add page anchors and intervention notes.

**Gate:** no production chunk boundaries or print furniture are visible in a
clean reading view; retained-word and structural checks pass.

### Phase 4 — Design-system rebuild

- Replace the current visual tokens and component styles.
- Rebuild home, works index, work page, parallel viewer, search, methodology,
  scoreboard/audit, genre, cipher, and tool pages from a shared component set.
- Validate desktop, tablet, mobile, print, light, and dark modes.

**Gate:** representative pages from every content class pass visual,
responsive, accessibility, and print review.

### Phase 5 — Editorial review batches

Review in this order:

1. Short prose works with clean witnesses.
2. Theological and monastic prose.
3. Sermons, verse, prayers, and hagiography.
4. Chronicles and very long works.
5. Polygraphia, Steganographia, keys, tables, sigils, and image-linked texts.

Each batch receives a human spot-check before deployment. Findings feed back
into shared rules, but rules are never broadened solely to make metrics pass.

**Gate:** signed review checklist for every batch.

### Phase 6 — Release candidate and public replacement

- Rebuild all pages and search indexes from a clean tree.
- Run metadata, link, structure, retained-content, accessibility, and visual
  regression checks.
- Review a release-candidate deployment rather than the production URL.
- Publish only after representative manual reading from every content class.

**Gate:** no unresolved blocker in the editorial ledger and no unsupported
quality claim in the public interface.

## 6. Required automated checks

- No visible `[segment N]` or source-page marker in clean reading views.
- No known running head, catchword, folio number, library stamp, or calibration
  text in clean reading views.
- Minimum retained-content thresholds with per-work exceptions documented.
- Stable tables, code fences, sigil references, and cipher sequences.
- Valid heading hierarchy and unique anchors.
- No empty or duplicate sections.
- No broken internal links or missing assets.
- Search index newer than rendered pages.
- Responsive overflow checks for tables and long tokens.
- Contrast, keyboard, landmark, and reduced-motion checks.
- Print rendering smoke tests.

## 7. Human review checklist

For each review batch, manually inspect:

- opening, middle, and ending passages;
- at least five page joins;
- every heading transition;
- lists, verse, tables, quotations, and notes;
- passages marked unclear or damaged;
- title, metadata, citation, and source links;
- mobile and print rendering;
- accuracy of the status notice and known-issues summary.

## 8. Immediate next actions

1. Implement the new evidence fields without deleting historical grade data.
2. Remove `S` and grade-prestige language from public templates and copy.
3. Generate the whole-corpus editorial ledger for `works/` and `works-t4b/`.
4. Inventory and screenshot every page type before redesign.
5. Produce two visual directions using representative prose, sermon, and cipher
   pages; select one before rebuilding all templates.
6. Process the earlier `works/` track through the same structural audit already
   piloted on T4B.

