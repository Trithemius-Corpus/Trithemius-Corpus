# IIIF facsimile foundation

The corpus publishes normalized [IIIF Presentation API 3](https://iiif.io/api/presentation/3.0/) manifests for three representative editions. These manifests preserve institutional attribution and rights, expose the provider's image services, group chapter-level canvas ranges, and attach English passages as supplementing annotations.

## Curatorial model

`data/iiif_sources.json` is the reviewed source registry. It records the provider manifest and API version, institutional record, rights URI, required attribution, page offset, and whether text-to-image alignment is exact or approximate. `scripts/iiif_model.py` discovers official BSB, Gallica, and e-rara endpoints and normalizes IIIF Presentation 2 provider data into Presentation 3.

Provider responses are metadata snapshots under `data/iiif/provider/`. Refreshing them is explicit:

```console
python scripts/iiif_model.py --refresh
```

Ordinary builds use those snapshots and make no network request. We do not mirror whole books. Image pixels remain on institutional IIIF services, while the readable Latin and English remain local and usable if a remote service or CORS policy fails.

## Alignment

Each corpus source segment already records one or more printed scan-page numbers. A passage targets the first canvas associated with its segment. The manifest's `Text alignment` metadata and the work page distinguish `exact` from `approximate`; no region coordinates are claimed until positional OCR or human zoning supplies evidence.

The focused OpenSeadragon viewer accepts `#canvas=N`. The work reader updates its Facsimile link as the active passage changes, so an exact passage URL opens the corresponding canvas. Attribution and the institutional source link remain visible outside the image surface and survive full-window use.

## Provider fallbacks

- BSB: official Presentation 2 and Image 2 APIs; institutional record is the persistent fallback.
- BnF/Gallica: official Presentation manifest and Gallica conditions-of-use URI; the ARK record is the persistent fallback.
- e-rara: official `i3f/v20/{VLID}/manifest` discovery is tested, ready for a curated pilot.
- HAB: retain the persistent digitized-book record until an edition-level IIIF endpoint is verified.
- dilibri: retain the persistent title record and downloadable files until an edition-level IIIF endpoint is verified.
- Internet Archive: prefer a verified `iiif.archive.org` manifest when present; otherwise retain the item page and original-file links.

Run `python scripts/validate_iiif.py` after building to check required statements, rights, painting annotations, text targets, ranges, and discovery contracts.
