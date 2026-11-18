"""Build a fresh Pagefind bundle and check it before replacing published search."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess

from publication_guard import staged_directory
from validate_reader_tools import ROOT, check

VERSION = "1.5.2"


def build(dist: Path, binary: str | None) -> None:
    dist = dist.resolve()
    binary = binary or os.environ.get("PAGEFIND_BIN") or shutil.which("pagefind")
    if binary:
        command = [binary]
    else:
        npx = shutil.which("npx")
        if not npx:
            raise ValueError("Provide a Pagefind executable with --pagefind or install npm for npx.")
        command = [npx, "--yes", f"pagefind@{VERSION}"]
    version = subprocess.check_output([*command, "--version"], text=True).strip()
    if VERSION != version.split()[-1]:
        raise ValueError(f"Expected Pagefind {VERSION}. Found {version}.")
    with staged_directory(dist / "pagefind", seed=False, lock_target=dist) as stage:
        check(dist, before_index=True)
        subprocess.run([*command, "--site", str(dist), "--output-path", str(stage)], check=True)
        pages, targets = check(dist, bundle=stage)
    print(f"Published local search for {pages} pages with {targets} indexed passage targets.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "site/dist")
    parser.add_argument("--pagefind", help=f"Path to Pagefind {VERSION}, default PAGEFIND_BIN or PATH")
    args = parser.parse_args()
    build(args.dist, args.pagefind)
