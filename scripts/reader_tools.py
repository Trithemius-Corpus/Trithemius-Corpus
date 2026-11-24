"""Searchable reader anchors and the vocabulary shipped to the parallel reader."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from passage_model import _BlockSpanParser, plain_text

COLLECTION = re.compile(r'<meta data-pagefind-filter="collection\[content\]" content="(?:editions|guides)">')
REVISION = re.compile(r'\n<meta data-pagefind-meta="sourceRevision\[content\]" content="[0-9a-f]{64}">')


def stamped_page(page: str) -> tuple[str, str]:
    """Bind each Pagefind document to the exact published HTML, across Git line endings."""
    source = REVISION.sub("", page.replace("\r\n", "\n"))
    revision = hashlib.sha256(source.encode()).hexdigest()
    element = f'\n<meta data-pagefind-meta="sourceRevision[content]" content="{revision}">'
    return COLLECTION.sub(lambda match: match.group() + element, source, count=1), revision


def stamp_search_pages(dist: Path) -> None:
    # Published book pages, genres and guides are the only indexed resources.
    for pattern in ("*.html", "genres/*.html", "works/*.html"):
        for path in dist.glob(pattern):
            previous = path.read_text(encoding="utf-8")
            if COLLECTION.search(previous):
                current, _ = stamped_page(previous)
                if current != previous:
                    path.write_text(current, encoding="utf-8", newline="\n")


def search_catalog(works, group_key, edition_label):
    """Use the catalogue's work grouping and printed-witness identity on both tracks."""
    editions = sorted(works, key=lambda w: (str(w.get("source_year") or w.get("year") or ""), w["id"]))
    titles = {}
    catalog = {}
    for work in editions:
        key = group_key(work)
        title = titles.setdefault(key, work.get("title_en") or work["title"])
        witness_id = work["id"]
        if witness_id in catalog:
            raise ValueError(f"Duplicate printed-witness identifier {witness_id}")
        catalog[witness_id] = {
            "group": key,
            "title": title,
            "witness": edition_label(work) or witness_id,
        }
    return catalog


def search_anchors(rendered: str, prefix: str, published_ids: dict | None = None) -> str:
    """Give unnumbered translation or editorial blocks text-based permalinks.

    Identical blocks receive occurrence suffixes. Existing edition anchors stay
    in place, including headings with published Markdown slugs.
    """
    blocks = _BlockSpanParser(rendered)
    blocks.feed(rendered)
    blocks.close()
    occurrences = {}
    assigned = set()
    pending = set(published_ids or {})
    parts = []
    end = 0
    for block in blocks.blocks:
        text = plain_text(rendered[block.start:block.end])
        if not text:
            continue
        signature = hashlib.sha256(text.encode()).hexdigest()[:16]
        occurrence = occurrences.get(signature, 0) + 1
        occurrences[signature] = occurrence
        anchor = f"{prefix}-{signature}" + (f"-{occurrence}" if occurrence > 1 else "")
        if published_ids:
            pending.discard(anchor)
            anchor = published_ids.get(anchor, anchor)
            if anchor in assigned:
                raise ValueError(f"Duplicate published reading anchor: {anchor}")
            assigned.add(anchor)
        parts.append(rendered[end:block.start])
        opening = rendered[block.start:block.start_tag_end]
        if "id" in block.attrs:
            parts.extend([f'<span id="{anchor}"></span>', opening])
        else:
            parts.append(f'{opening[:-1]} id="{anchor}">')
        end = block.start_tag_end
    parts.append(rendered[end:])
    if pending:
        raise ValueError("Corrected text no longer renders at its published reading anchor")
    return "".join(parts)


def reader_glossary(root: Path) -> dict:
    entries = []
    for line in (root / "data/lexicon/glossary.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            entries.append({**entry, "source": "editorial"})
    technical = json.loads((root / "site/static/lexicon.json").read_text(encoding="utf-8"))
    for term, value in technical["terms"].items():
        definition = {"en": value} if isinstance(value, str) else value
        # 'figur' is a stem in the historical display glossary. Spell out the
        # noun's forms so unrelated words sharing that prefix do not match.
        forms = ["figur", "figura", "figurae", "figuram", "figurarum", "figuras", "figuris"] if term == "figur" else [term]
        entries.append({
            "lemma": "figura" if term == "figur" else term, "forms": forms,
            "en": definition["en"], "note": definition.get("note", ""),
            "clusters": ["crypto-occult"], "source": "technical",
        })
    return {"version": 1, "entries": entries}


def publish_glossary(root: Path, dist: Path) -> None:
    output = dist / "static/reader-glossary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(reader_glossary(root), ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
