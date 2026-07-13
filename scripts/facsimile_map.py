"""Shared chunk -> source-page mapping for Style C facsimile pairing.

The Style C chunk `.md` files carry no `--- Page NNN ---` markers (the cipher
renderers strip them while building their tables). The only robust way to learn
which source page a Style C chunk came from is to re-chunk the working-corpus
`full.txt` with the *same* harness chunker that produced the chunks, and read
the page markers out of each record. Record i (1-based) == `full_chunk_{i:04d}`,
the global chunk index the Style C filenames carry.

This mirrors `build_site.py`'s parallel-viewer re-chunk exactly
(`records_from_file(full_txt, None, 4500, 0, True)`), so chunk-index alignment
cannot drift as long as those parameters stay in lockstep.

Page markers are 1:1 with `data/corpus/<work>/pages/page_NNN.png` (verified:
546 markers == 546 PNGs for prdl-70282, etc.), zero-padded to 3 digits.

Both `build_facsimiles.py` (to know which pages to encode) and `build_site.py`
(to attach `chunk["pages"]`) import from here.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"
HARNESS_SCRIPTS = WORKING / "scripts"

# Must match the parameters that produced the translations / Style C chunks.
CHUNK_MAX_CHARS = 4500
CHUNK_OCR_CLEANUP = True

# Style C content types that get a per-chunk source facsimile.
STYLE_C_TYPES = ("cipher-key", "cipher-grid", "untranslated", "prose-damaged")

PAGE_MARKER_RE = re.compile(r"---\s*Page\s+(\d+)\s*---")
CHUNK_INDEX_RE = re.compile(r"full_chunk_(\d+)")

_chunker = None
_rec_pages_cache: dict[str, dict[int, list[int]]] = {}


def get_chunker():
    """Lazily import the harness chunker; None if unavailable (degrade)."""
    global _chunker
    if _chunker is None:
        if str(HARNESS_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(HARNESS_SCRIPTS))
        try:
            from latin_translation_harness import records_from_file
            _chunker = records_from_file
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] harness chunker unavailable ({e}); "
                  f"facsimile mapping will be skipped")
            _chunker = False
    return _chunker or None


def rec_pages_for_work(work_id: str) -> dict[int, list[int]]:
    """Return {chunk_index: [source page numbers]} for a work.

    Empty dict if the working corpus / chunker is unavailable (caller degrades
    to no facsimiles). Cached per work so build_site and build_facsimiles do
    not double-chunk."""
    if work_id in _rec_pages_cache:
        return _rec_pages_cache[work_id]
    chunker = get_chunker()
    full_txt = CORPUS / work_id / "full.txt"
    if chunker is None or not full_txt.exists():
        _rec_pages_cache[work_id] = {}
        return {}
    recs = chunker(full_txt, None, CHUNK_MAX_CHARS, 0, CHUNK_OCR_CLEANUP)
    out: dict[int, list[int]] = {}
    for i, rec in enumerate(recs, 1):
        pages = sorted({int(m) for m in PAGE_MARKER_RE.findall(rec["text"])})
        out[i] = pages
    _rec_pages_cache[work_id] = out
    return out


def style_c_chunk_indices(
    work_id: str, types: tuple[str, ...] = STYLE_C_TYPES
) -> dict[int, list[str]]:
    """Return {chunk_index: [content_types...]} for chunks that have a Style C
    rendering of one of `types` in the working corpus."""
    out: dict[int, list[str]] = {}
    for t in types:
        d = CORPUS / work_id / "translations" / f"style-c-{t}" / "full"
        if not d.is_dir():
            continue
        for f in d.glob("full_chunk_*.md"):
            m = CHUNK_INDEX_RE.search(f.stem)
            if m:
                out.setdefault(int(m.group(1)), []).append(t)
    return out


def pages_for_chunk(
    work_id: str, chunk_index: int, rec_pages: dict[int, list[int]] | None = None
) -> tuple[list[int], bool]:
    """Source pages for one chunk. Returns (pages, approx).

    A handful of chunks have no marker (a `--- Page ---` fell exactly on a
    chunk boundary and attached to a neighbour); for those we borrow the
    nearest neighbour record's adjoining page and flag it approximate."""
    rp = rec_pages if rec_pages is not None else rec_pages_for_work(work_id)
    pages = rp.get(chunk_index, [])
    if pages:
        return pages, False
    prev = rp.get(chunk_index - 1, [])
    if prev:
        return [prev[-1]], True
    nxt = rp.get(chunk_index + 1, [])
    if nxt:
        return [nxt[0]], True
    return [], False


def cipher_pages_for_work(
    work_id: str, types: tuple[str, ...] = STYLE_C_TYPES
) -> list[int]:
    """Union of all source pages referenced by this work's Style C chunks of
    the given types (the page set `build_facsimiles.py` must encode)."""
    rp = rec_pages_for_work(work_id)
    pages: set[int] = set()
    for idx in style_c_chunk_indices(work_id, types):
        pg, _ = pages_for_chunk(work_id, idx, rp)
        pages.update(pg)
    return sorted(pages)
