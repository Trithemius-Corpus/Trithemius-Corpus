# Unified study reader

Every work page remains a complete server-rendered English reading edition. JavaScript progressively adds three views over the same stable passage cursor:

- **Read** keeps the quiet single-column edition.
- **Study** pairs the English passage with its diplomatic Latin OCR segment, chapter minimap, progress, search density, and annotation controls.
- **Source** pairs the English passage with the aligned institutional facsimile for IIIF pilots.

The selected mode is encoded as `?view=read`, `?view=study`, or `?view=source`; the stable passage remains the URL fragment. Theme, typography, mode, viewport changes, search, and layer switches do not replace that fragment. Copied passage links also carry language and annotation-layer state.

## Progressive enhancement and synchronization

Aligned Latin is loaded from the existing passage index rather than duplicated in HTML. If loading fails, the full English remains and the permanent parallel-viewer link is still available. Source mode lazy-loads the IIIF viewer; institutional images are never a prerequisite for reading.

English scroll position drives the Latin segment, progress bar, and source canvas. Canvas changes inside the embedded viewer report back to the parent and highlight the first passage mapped to that canvas. Region-level highlighting is activated only when a future mapping supplies evidence-backed coordinates; current mappings deliberately claim canvas precision only.

## Access and presentation

- Mode controls are ordinary links, so URLs remain inspectable and copyable.
- Search is keyboard-operable and reports its current match through a live output.
- Note previews use the browser Popover API where supported and retain the positioned tooltip fallback.
- Focus targets use a sticky-header offset and a strong visible outline.
- At narrow widths, study and source views stack intentionally instead of compressing columns.
- Print always emits the complete English and removes reader chrome and auxiliary panes.
- Reduced-motion preferences disable study progress animation and existing scroll helpers.

Run `python scripts/validate_study_reader.py` after the site build, alongside the reader, passage, IIIF, and release validators.
