"""Structural acceptance checks for generated Trithemius 4B reading pages."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T4B_ROOT = ROOT / "works-t4b"
DIST_ROOT = ROOT / "site" / "dist" / "works"


class ReadingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_body = False
        self.body_div_depth = 0
        self.text: list[str] = []
        self.segments = 0
        self.headings = 0
        self.tables = 0
        self.pre = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "div" and "english-body" in classes:
            self.in_body = True
            self.body_div_depth = 1
        elif self.in_body and tag == "div":
            self.body_div_depth += 1
        if not self.in_body:
            return
        if tag == "section" and "segment" in classes:
            self.segments += 1
        if tag in {"h2", "h3", "h4", "h5"}:
            self.headings += 1
        if tag == "table":
            self.tables += 1
        if tag == "pre":
            self.pre += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.in_body:
            self.body_div_depth -= 1
            if self.body_div_depth == 0:
                self.in_body = False

    def handle_data(self, data: str) -> None:
        if self.in_body:
            self.text.append(data)


def source_word_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^\[segment \d+\]\s*$|^--- Page \d+ ---\s*$", "", text)
    return len(re.findall(r"\b[\w’'-]+\b", text))


def main() -> int:
    failures: list[str] = []
    summaries: list[str] = []
    for work_dir in sorted(p for p in T4B_ROOT.iterdir() if p.is_dir()):
        source = work_dir / "english.md"
        rendered = DIST_ROOT / f"{work_dir.name}-trithemius-4b.html"
        if not source.exists() or not rendered.exists():
            failures.append(f"{work_dir.name}: missing source or rendered page")
            continue
        parser = ReadingParser()
        parser.feed(rendered.read_text(encoding="utf-8"))
        rendered_text = " ".join(parser.text)
        rendered_words = len(re.findall(r"\b[\w’'-]+\b", rendered_text))
        source_words = source_word_count(source)
        coverage = rendered_words / source_words if source_words else 1.0
        if coverage < 0.75:
            failures.append(f"{work_dir.name}: only {coverage:.1%} word coverage")
        if parser.segments < 1:
            failures.append(f"{work_dir.name}: no rendered reading section")
        summaries.append(
            f"{work_dir.name[:48]:48} coverage={coverage:6.1%} "
            f"sections={parser.segments:3} headings={parser.headings:3} "
            f"tables={parser.tables:3} pre={parser.pre:3}"
        )
    print("\n".join(summaries))
    if failures:
        print("\nFAILURES")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print(f"\nAll {len(summaries)} T4B reading pages passed structural checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
