"""Generate the featured-work landing thumbnails (site/static/images/thumbnails/
<prdl-id>.webp) from each work's first readable facsimile page.

These are the small images shown on the homepage "Start here" section. Missing
ones just hide via onerror, but generating them improves the landing page.
"""
import sys
import os
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "site" / "dist" / "static" / "images"
OUT = DIST / "thumbnails"
OUT.mkdir(parents=True, exist_ok=True)

WORKS = DIST
SRC_PAGES = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius")) / "data" / "corpus"

# Featured work ids (prefix only) needing thumbnails
NEEDED = ["prdl-32287", "prdl-24373", "prdl-24395", "prdl-24362", "prdl-24386",
          "prdl-24390", "prdl-70280"]

THUMB_W = 400
QUALITY = 72


def find_first_page(prefix: str) -> Path | None:
    # 1) webp facsimiles in the corpus site
    for d in WORKS.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            pages = sorted(d.glob("page_*.webp"))
            pages = [p for p in pages if "_thumb" not in p.name]
            for p in pages[:15]:
                if p.stat().st_size > 15000:
                    return p
            return pages[0] if pages else None
    # 2) raw PNG page scans in the source repo
    for d in SRC_PAGES.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            pages = sorted((d / "pages").glob("page_*.png")) if (d / "pages").exists() else []
            for p in pages[:15]:
                if p.stat().st_size > 30000:
                    return p
            return pages[0] if pages else None
    return None


def main():
    for prefix in NEEDED:
        dst = OUT / f"{prefix}.webp"
        if dst.exists() and dst.stat().st_size > 1000:
            print(f"  {prefix}: exists ({dst.stat().st_size//1024} KB)")
            continue
        src = find_first_page(prefix)
        if not src:
            print(f"  {prefix}: NO SOURCE IMAGE")
            continue
        im = Image.open(src).convert("RGB")
        w, h = im.size
        if w > THUMB_W:
            nh = int(h * THUMB_W / w)
            im = im.resize((THUMB_W, nh), Image.LANCZOS)
        im.save(dst, "WEBP", quality=QUALITY, method=6)
        print(f"  {prefix}: made {dst.name} ({dst.stat().st_size//1024} KB) from {src.name}")


if __name__ == "__main__":
    main()
