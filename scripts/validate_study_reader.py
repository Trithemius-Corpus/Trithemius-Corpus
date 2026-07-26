"""Contract checks for the progressively enhanced unified study reader."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "site" / "dist"
PILOTS = (
    "prdl-24362_de-laude-scriptorum-manualium",
    "prdl-24390_polygraphiae-libri-vi",
    "prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam",
)


class ContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.modes: set[str] = set()
        self.passages = 0
        self.source_iframe_src: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"] or "")
        if values.get("data-reader-mode"):
            self.modes.add(values["data-reader-mode"] or "")
        if values.get("data-passage-id"):
            self.passages += 1
        if values.get("id") == "study-source-frame":
            self.source_iframe_src = values.get("src")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    reader = (ROOT / "site" / "static" / "reader.js").read_text(encoding="utf-8")
    style = (ROOT / "site" / "static" / "style.css").read_text(encoding="utf-8")
    template = (ROOT / "site" / "templates" / "work.html.j2").read_text(encoding="utf-8")
    for token in ("tc:passage", "tc:canvas", "data-reader-mode", "study-search-match",
                  "iiifCanvasMap", "history.replaceState"):
        require(token in reader, f"reader.js missing {token}")
    for token in ("data-mode=\"study\"", "data-mode=\"source\"", "max-width: 850px",
                  "prefers-reduced-motion", "@media print", "scroll-margin-top"):
        require(token in style, f"style.css missing {token}")
    require("study-source-frame" in template and 'loading="lazy"' in template,
            "source iframe must be lazy")
    require("{{ english|safe }}" in template, "server-rendered English fallback missing")

    total_passages = 0
    for work_id in PILOTS:
        page = DIST / "works" / f"{work_id}.html"
        parser = ContractParser()
        parser.feed(page.read_text(encoding="utf-8"))
        require(parser.modes == {"read", "study", "source"}, f"{work_id}: mode controls")
        for expected in ("study-reader", "rt-work-search", "rt-match-strip", "study-minimap",
                         "study-latin-content", "study-source-frame"):
            require(expected in parser.ids, f"{work_id}: missing #{expected}")
        require(parser.passages > 0, f"{work_id}: progressive English fallback")
        require(parser.source_iframe_src is None, f"{work_id}: source iframe must not load in Read mode")
        index = json.loads((DIST / "data" / "passages" / f"{work_id}.json").read_text(encoding="utf-8"))
        require(index.get("segments") and all("latin" in item for item in index["segments"]),
                f"{work_id}: Latin study data")
        total_passages += parser.passages
    print("Study reader validation passed.")
    print(f"  pilot pages: {len(PILOTS)}")
    print(f"  server-rendered pilot passages: {total_passages}")
    print("  modes: Read, Study, Source")


if __name__ == "__main__":
    main()
