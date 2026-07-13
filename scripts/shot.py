"""Headless-Chrome screenshot helper for the Trithemius Corpus.

Captures full-page PNGs (and mobile viewport shots) of each page template so
issues can be reviewed visually. Usage:

    python scripts/shot.py [desktop|mobile|both] [page1 page2 ...]
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = (ROOT / "site" / "dist").resolve()
OUT = Path(os.environ.get("TRITHEMIUS_SHOTS_DIR", ROOT / ".cache" / "shots"))
OUT.mkdir(parents=True, exist_ok=True)

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# (label, relative-path, [extra-flags])  -- representative of each template
PAGES = [
    ("01_index", "index.html", []),
    ("02_works", "works.html", []),
    ("03_scoreboard", "scoreboard.html", []),
    ("04_methodology", "methodology.html", []),
    ("05_ciphers", "ciphers.html", []),
    ("06_search", "search.html", []),
    ("07_404", "404.html", []),
    ("08_workpage", "works/prdl-24390_polygraphiae-libri-vi.html", []),
    ("09_workpage_short", "works/prdl-24362_de-laude-scriptorum-manualium.html", []),
    ("10_parallel", "works/prdl-24390_polygraphiae-libri-vi_parallel.html", []),
    ("11_stylec_cipherkey", "works/prdl-24390_polygraphiae-libri-vi_style-c-cipher-key.html", []),
    ("12_stylec_ciphergrid", "works/prdl-24390_polygraphiae-libri-vi_style-c-cipher-grid.html", []),
    ("15_stylec_damaged", "works/prdl-24390_polygraphiae-libri-vi_style-c-prose-damaged.html", []),
    ("16_genre", "genres/crypto-occult.html", []),
]


def shoot(label: str, rel: str, mode: str):
    url = (DIST / rel).as_uri()
    if mode == "desktop":
        w, h = 1366, 9000
        suffix = ""
    else:
        w, h = 390, 9000
        suffix = "_m"
    out_png = OUT / f"{label}{suffix}.png"
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-sandbox",
        "--force-device-scale-factor=1",
        "--disk-cache-size=1",
        "--media-cache-size=1",
        "--disable-application-cache",
        f"--user-data-dir={OUT / '_chrome_profile'}",
        f"--window-size={w},{h}",
        f"--screenshot={out_png}",
        "--virtual-time-budget=2500",
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        print(f"  {label}{suffix}: TIMEOUT")
        return
    if out_png.exists():
        print(f"  {label}{suffix}: {out_png.stat().st_size//1024} KB")
    else:
        print(f"  {label}{suffix}: MISSING")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    pages = sys.argv[2:] if len(sys.argv) > 2 else None
    modes = ["desktop", "mobile"] if mode == "both" else [mode]
    for m in modes:
        print(f"=== {m} ===")
        for label, rel, _ in PAGES:
            if pages and not any(p in label or p in rel for p in pages):
                continue
            shoot(label, rel, m)


if __name__ == "__main__":
    main()
