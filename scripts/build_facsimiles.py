"""Encode source-page facsimiles (WebP) for the Style C cipher renderings.

For every source page that a Style C chunk of a crypto-occult work draws from,
downscale the working-corpus PNG scan into a web-friendly WebP (a full view for
click-to-zoom + a thumbnail for the inline figure) under
`site/static/images/<work_id>/`. `build_site.py`'s `copy_static()` then mirrors
that tree into `site/dist/static/images/`, which is what GitHub Pages serves.

The page set per work comes from `facsimile_map.cipher_pages_for_work` — the
same re-chunk-and-read-`--- Page NNN ---` mapping the site uses to attach
facsimiles to chunks, so the encoded set and the referenced set always agree.

Idempotent: a page is skipped if its WebP exists and is newer than the source
PNG. Run before `build_site.py`.

Usage:
    python scripts/build_facsimiles.py                 # all crypto works, all Style C types
    python scripts/build_facsimiles.py --work prdl-70282_clavis-...
    python scripts/build_facsimiles.py --tier cipher   # cipher-key + cipher-grid pages only
    python scripts/build_facsimiles.py --force         # re-encode even if up to date
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

# Archival scans (BSB/dilibri) run to ~9067x14200 (~128 MP), above Pillow's
# default decompression-bomb ceiling. These are trusted local public-domain
# scans, so lift the guard rather than have it abort the encode.
Image.MAX_IMAGE_PIXELS = None

SCR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCR))
import facsimile_map as fm  # noqa: E402

ROOT = SCR.parent
IMAGES_OUT = ROOT / "site" / "static" / "images"

# The crypto-occult cluster: the only works with Style C renderings + page scans.
CRYPTO_WORKS = [
    "prdl-24389_polygraphiae-libri-sex-ioannis-trithemii-abbatis",
    "prdl-24390_polygraphiae-libri-vi",
    "prdl-24391_polygraphiae-libri-vi",
    "prdl-70282_clavis-polygraphiae-ioannis-trithemii-abbatis-diui",
    "prdl-70281_clavis-generalis-triplex-in-libros-steganographicos",
    "prdl-32286_octo-quaestionum-maximilianum-caesarem",
    "prdl-70286_octo-quaestionum-maximilianum-caesarem",
    "prdl-70291_dilibri_veterum-sophorum-sigilla-et-imagines-magicae",
    "prdl-70292_e-rara_veterum-sophorum-sigilla-et-imagines",
    "prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam",
]

TIER_TYPES = {
    "all": fm.STYLE_C_TYPES,                       # every Style C chunk's page (default)
    "cipher": ("cipher-key", "cipher-grid"),       # the substitution tables
    "grid": ("cipher-grid",),                       # the provably-collapsed grids only
}

FULL_WIDTH = 1400      # full-view max width (px); dense cipher tables need legibility
THUMB_WIDTH = 480      # inline-figure thumbnail width (px)
QUALITY = 72           # WebP quality; ~115 KB full / ~29 KB thumb on a 1025x1417 scan


def _encode(src: Path, dst: Path, width: int, quality: int) -> int:
    """Downscale `src` to max `width` and save WebP `dst`. Returns bytes written."""
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > width:
            h = round(im.height * width / im.width)
            im = im.resize((width, h), Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "WEBP", quality=quality, method=6)
    return dst.stat().st_size


def _up_to_date(src: Path, dst: Path) -> bool:
    return dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime


def build_work(work_id: str, types: tuple[str, ...], force: bool) -> tuple[int, int, int]:
    """Encode all facsimile pages for one work. Returns (encoded, skipped, bytes)."""
    pages_dir = fm.CORPUS / work_id / "pages"
    if not pages_dir.is_dir():
        print(f"  [skip] {work_id}: no pages/ directory")
        return 0, 0, 0
    page_nums = fm.cipher_pages_for_work(work_id, types)
    if not page_nums:
        print(f"  [skip] {work_id}: no Style C pages for tier")
        return 0, 0, 0
    out_dir = IMAGES_OUT / work_id
    encoded = skipped = total_bytes = 0
    missing: list[int] = []
    for n in page_nums:
        src = pages_dir / f"page_{n:03d}.png"
        if not src.exists():
            missing.append(n)
            continue
        full_dst = out_dir / f"page_{n:03d}.webp"
        thumb_dst = out_dir / f"page_{n:03d}_thumb.webp"
        for dst, width in ((full_dst, FULL_WIDTH), (thumb_dst, THUMB_WIDTH)):
            if not force and _up_to_date(src, dst):
                skipped += 1
                total_bytes += dst.stat().st_size
                continue
            total_bytes += _encode(src, dst, width, QUALITY)
            encoded += 1
    note = f"  {work_id}: {len(page_nums)} pages -> encoded {encoded}, skipped {skipped}"
    if missing:
        note += f", {len(missing)} source PNG missing ({missing[:5]}...)"
    print(note)
    return encoded, skipped, total_bytes


def main() -> int:
    global FULL_WIDTH, QUALITY
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="", help="single work id (default: all crypto works)")
    ap.add_argument("--tier", choices=sorted(TIER_TYPES), default="all")
    ap.add_argument("--force", action="store_true", help="re-encode even if up to date")
    ap.add_argument("--full-width", type=int, default=FULL_WIDTH,
                    help=f"full-view max width px (default {FULL_WIDTH}; lower = smaller repo)")
    ap.add_argument("--quality", type=int, default=QUALITY,
                    help=f"WebP quality (default {QUALITY})")
    args = ap.parse_args()

    FULL_WIDTH = args.full_width
    QUALITY = args.quality

    if fm.get_chunker() is None:
        print("ERROR: harness chunker unavailable; cannot map chunks to pages.", file=sys.stderr)
        return 2

    works = [args.work] if args.work else CRYPTO_WORKS
    types = TIER_TYPES[args.tier]
    enc = skip = total = 0
    for w in works:
        e, s, b = build_work(w, types, args.force)
        enc += e
        skip += s
        total += b
    print(f"\nfacsimiles: tier={args.tier}  encoded {enc}, skipped {skip}, "
          f"~{total / 1024 / 1024:.0f} MB under site/static/images/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
