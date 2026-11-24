"""Refresh editorial copy from sources without rebuilding the reading text.

This bounded build uses the committed site as its base. Only work
headers, metadata, introductions, Book JSON-LD, and shared footers are replaced;
reading bodies, apparatus, passage indexes, and source mappings stay intact.
Landing/catalogue pages and editorial documentation use the normal builders.

Run publication exports and Pagefind afterwards to refresh their copies too.
"""
from __future__ import annotations

import re
from pathlib import Path

import build_site as bs
import build_t4b_pages as t4b


WORK_BLOCKS = (
    r'<header class="work-header">.*?</header>',
    r'<section class="work-meta">.*?</section>',
    r'<section class="work-intro"[^>]*>.*?</section>',
)
FOOTER = r'<p class="footer-byline muted">.*?</p>'
JSONLD = r'<script type="application/ld\+json">.*?</script>'


def replace_block(old: str, new: str, pattern: str) -> str:
    """Replace exactly one known, non-nested template block or fail closed."""
    existing = list(re.finditer(pattern, old, re.S))
    replacement = list(re.finditer(pattern, new, re.S))
    if len(existing) != 1 or len(replacement) != 1:
        raise ValueError(f"expected one block for {pattern!r}, got {len(existing)}/{len(replacement)}")
    a, b = existing[0], replacement[0]
    return old[:a.start()] + b.group() + old[a.end():]


def protected_content(page: str) -> str:
    """Everything outside the permitted editorial blocks, byte for byte."""
    for pattern in (*WORK_BLOCKS, JSONLD):
        page = re.sub(pattern, "", page, flags=re.S)
    return page


def save_if_changed(path: Path, text: str) -> None:
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")


def refresh() -> None:
    env = bs.make_env()
    manifest = bs.load_manifest()
    works = [bs.enrich_work(w) for w in manifest["works"] if not w["skip"]]
    bs.attach_editions(works)
    texts = bs.build_texts(works)
    sections = bs.genre_sections(texts, bs.load_clusters())
    bs.ALL_WORK_IDS = [w["id"] for w in works]
    generated: dict[Path, str] = {}

    for work in works:
        path = bs.OUT / "works" / f"{work['id']}.html"
        old = path.read_text(encoding="utf-8")
        rendered = bs.build_work(env, work, "", True, None)
        updated = old
        for pattern in (*WORK_BLOCKS, JSONLD):
            updated = replace_block(updated, rendered, pattern)
        if protected_content(old) != protected_content(updated):
            raise ValueError(f"reading content changed: {path.name}")
        generated[path] = updated

    t4b_works = t4b.load_t4b_works()
    for work in t4b_works:
        path = bs.OUT / "works" / f"{work['id']}-trithemius-4b.html"
        old = path.read_text(encoding="utf-8")
        rendered = t4b.build_t4b_work_page(env, work)
        updated = old
        for pattern in (*WORK_BLOCKS, JSONLD):
            updated = replace_block(updated, rendered, pattern)
        if protected_content(old) != protected_content(updated):
            raise ValueError(f"reading content changed: {path.name}")
        generated[path] = updated

    generated[bs.OUT / "index.html"] = bs.build_index(env, manifest, works, texts, sections)
    generated[bs.OUT / "works.html"] = bs.build_works_page(env, works, texts, sections)
    generated[bs.OUT / "scoreboard.html"] = bs.build_scoreboard(env, works)
    generated[bs.OUT / "works-trithemius-4b.html"] = t4b.build_t4b_index(env, t4b_works)
    for section in sections:
        generated[bs.OUT / "genres" / f"{section['slug']}.html"] = bs.build_genre_page(env, section)
    for title, source, slug in (
        ("Methodology", "METHODOLOGY.md", "methodology.html"),
        ("Prior English translations", "docs/PRIOR_TRANSLATIONS.md", "prior-translations.html"),
    ):
        generated[bs.OUT / slug] = bs.render_simple_page(
            env, title, bs.render_markdown_file(bs.ROOT / source), slug,
            description=("How the Trithemius Corpus was made: the OCR, translation, and grading "
                         "pipeline, per-work model provenance, and honest limitations."
                         if slug == "methodology.html" else
                         "The project bibliography survey: prior English translations, search scope, and uncertainties."),
            nav="methodology" if slug == "methodology.html" else None,
        )

    # Check all replacements before writing the first page.
    for path, page in generated.items():
        save_if_changed(path, page)
    t4b.link_t4b_into_main_pages(t4b_works)

    for path in sorted(bs.OUT.rglob("*.html")):
        old = path.read_text(encoding="utf-8")
        if not re.search(FOOTER, old, re.S):
            continue  # standalone facsimile and print views have no site footer
        relative = path.relative_to(bs.OUT)
        depth = len(relative.parts) - 1
        shell = env.get_template("base.html.j2").render(
            url=bs.make_url(depth, relative.parent.as_posix()), asset=bs.make_asset(depth),
        )
        save_if_changed(path, replace_block(old, shell, FOOTER))

    print(f"Refreshed editorial sections on {len(works)} standard and {len(t4b_works)} T4B pages.")
    print("Reading text, apparatus, and passage indexes preserved; catalogue, documentation, and footers refreshed.")


def main() -> int:
    with bs.staged_site():
        refresh()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
