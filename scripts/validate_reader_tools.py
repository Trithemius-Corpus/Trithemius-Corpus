"""Validate the published glossary and the passage destinations in Pagefind 1.5.2."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from lxml import html
from reader_tools import COLLECTION, reader_glossary, stamped_page

ROOT = Path(__file__).resolve().parents[1]


def fragments(bundle: Path) -> dict:
    docs = {}
    for path in (bundle / "fragment").glob("*.pf_fragment"):
        # Pagefind prefixes compressed JSON with a fixed binary format marker.
        raw = gzip.decompress(path.read_bytes())
        if not raw.startswith(b"pagefind_dcd{"):
            raise ValueError(f"{path.name}: unknown Pagefind fragment format")
        doc = json.loads(raw[len(b"pagefind_dcd"):])
        relative = doc["url"].lstrip("/")
        if not relative or relative.endswith("/"):
            relative += "index.html"
        if relative in docs:
            raise ValueError(f"duplicate search document {relative}")
        docs[relative] = doc
    return docs


def check(dist: Path, before_index: bool = False, bundle: Path | None = None) -> tuple[int, int]:
    if json.loads((dist / "static/reader-glossary.json").read_text(encoding="utf-8")) != reader_glossary(ROOT):
        raise ValueError("reader glossary differs from the editorial or technical source")
    search = html.parse(dist / "search.html")
    fields = search.xpath('//input[@type="search" or @type="text"]')
    if len(fields) != 1 or not search.xpath('//label[@for=$target]', target=fields[0].get("id")):
        raise ValueError("search needs one labelled query field")
    if search.xpath('//*[contains(@src,"pagefind-ui")]') or not search.xpath('//script[contains(@src,"corpus-search.mjs")]'):
        raise ValueError("incorrect search interface")
    documents = {} if before_index else fragments(bundle or dist / "pagefind")
    seen = set()
    total = 0
    for pattern in ("*.html", "genres/*.html", "works/*.html"):
        for path in sorted(dist.glob(pattern)):
            page = path.read_text(encoding="utf-8")
            relative = path.relative_to(dist).as_posix()
            if not COLLECTION.search(page):
                if pattern == "works/*.html":
                    raise ValueError(f"{relative}: missing corpus search metadata")
                continue
            stamped, version = stamped_page(page)
            if stamped != page:
                raise ValueError(f"{relative}: missing or stale search revision")
            seen.add(relative)
            if before_index:
                continue
            doc = documents.get(relative)
            if not doc or doc["meta"].get("sourceRevision") != version:
                raise ValueError(f"{relative}: Pagefind index differs from the packaged HTML")
            if pattern != "works/*.html":
                if doc["filters"].get("collection") != ["guides"]:
                    raise ValueError(f"{relative}: site guide unavailable in search")
                continue
            meta = doc["meta"]
            if doc["filters"].get("collection") != ["editions"] or not all(
                meta.get(key) for key in ("workGroup", "workTitle", "witness", "track", "view")
            ):
                raise ValueError(f"{relative}: incomplete edition identity in search")
            tree = html.fromstring(page, parser=html.HTMLParser(huge_tree=True))
            html_ids = set(tree.xpath('//*[@id]/@id'))
            found = {anchor["id"] for anchor in doc["anchors"]}
            if not found <= html_ids:
                raise ValueError(f"{relative}: index points to an absent HTML anchor")
            if meta["view"] == "latin":
                cells = tree.xpath('//*[@data-segment and @data-pagefind-body]')
                expected = {"latin-seg-" + e.get("data-segment") for e in cells}
                if not all("seg-" + e.get("data-segment") in html_ids for e in cells):
                    raise ValueError(f"{relative}: missing Latin reader target")
                if not tree.xpath('//*[@data-genre and @data-glossary="../static/reader-glossary.json"]'):
                    raise ValueError(f"{relative}: genre glossary not wired")
            elif meta["view"] == "apparatus":
                expected = {key for key in html_ids if key.startswith("rendering-full_chunk_")}
                if not all(key.removeprefix("rendering-") in html_ids for key in expected):
                    raise ValueError(f"{relative}: missing scholarly rendering target")
            elif meta["view"] == "translation":
                prefix = "p-t4b-" if meta["track"] == "Trithemius 4B" else "p-en-"
                expected = {key for key in html_ids if key.startswith((prefix, "note-intro-", "note-errata-"))}
                if not any(key.startswith(prefix) for key in expected):
                    raise ValueError(f"{relative}: missing searchable translation passages")
            else:
                raise ValueError(f"{relative}: unknown search view {meta['view']}")
            if not expected or expected - found:
                missing = sorted(expected - found)
                raise ValueError(f"{relative}: {len(missing)} unindexed passage targets {missing[:5]}")
            total += len(expected)
    if not before_index and seen != set(documents):
        raise ValueError(f"Unexpected search documents: {sorted(set(documents) - seen)}")
    return len(seen), total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "site/dist")
    parser.add_argument("--before-index", action="store_true", help="check source assets before running Pagefind")
    args = parser.parse_args()
    pages, targets = check(args.dist, args.before_index)
    print(f"Reader tools validated. {pages} searchable pages" +
          (" prepared for indexing." if args.before_index else f", {targets} indexed passage targets."))
