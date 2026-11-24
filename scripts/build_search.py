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


def enable_search_recovery(bundle: Path) -> None:
    """Keep Pagefind's worker and main-thread fallback on the same error contract.

    In 1.5.2 a failed index/filter load resolves successfully, and rejected
    resource promises stay cached. Neither condition is observable through its
    public search API. Match the pinned runtime exactly when staging a release.
    """
    replacements = [
        ("queued.resolve(await fetch(queued.input));",
         "const response=await fetch(queued.input);"
         "if(!response.ok)throw new Error('Pagefind HTTP '+response.status);queued.resolve(response);"),
        ("console.error(`Failed to load the index chunk ${url}:\n${e?.toString()}`);",
         "throw new Error(`Failed to load the index chunk ${url}`, {cause:e});"),
        ("console.error(`Decompressing ${file} appears to have failed: Missing signature`);return data;",
         "throw new Error('Invalid Pagefind signature: '+file);"),
    ]
    for cache, operation in (
        ("loaded_chunks", 'this._loadGenericChunk(url,"load_index_chunk")'),
        ("loaded_filters", 'this._loadGenericChunk(url,"load_filter_chunk")'),
        ("loaded_fragments", "this._loadFragment(hash)"),
    ):
        assignment = f"this.{cache}[hash]={operation}"
        replacements.append((assignment + ";", assignment + f".catch(error=>{{delete this.{cache}[hash];throw error;}});"))
    for name in ("pagefind.js", "pagefind-worker.js"):
        path = bundle / name
        original = path.read_text(encoding="utf-8")
        if f'const pagefind_version="{VERSION}";' not in original:
            raise ValueError(f"{name}: unexpected Pagefind version")
        if all(original.count(after) == 1 for _, after in replacements):
            continue
        updated = original
        for before, after in replacements:
            if updated.count(before) != 1:
                raise ValueError(f"{name}: expected Pagefind {VERSION} resource loader changed")
            updated = updated.replace(before, after)
        path.write_text(updated, encoding="utf-8", newline="\n")


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
        enable_search_recovery(stage)
        pages, targets = check(dist, bundle=stage)
    print(f"Published local search for {pages} pages with {targets} indexed passage targets.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "site/dist")
    parser.add_argument("--pagefind", help=f"Path to Pagefind {VERSION}, default PAGEFIND_BIN or PATH")
    args = parser.parse_args()
    build(args.dist, args.pagefind)
