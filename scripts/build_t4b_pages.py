"""Build standalone Trithemius 4B edition work pages.

Runs as a post-build step after build_site.py. Produces:
  site/dist/works/<id>-trithemius-4b.html         (27 standalone pages)
  site/dist/works-trithemius-4b.html              (index page listing all 27)

Each T4B page renders the LoRA OCR + GPT-5.5 translation with a clear
"Trithemius 4B edition" badge and Sonnet grade, and links back to the
corresponding published edition for comparison.
"""
from __future__ import annotations

import json
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
T4B_ROOT = ROOT / "works-t4b"

# Import helpers from build_site (same module dir)
import build_site as bs  # noqa: E402
import t4b_cleaners_cipher
import t4b_cleaners_devotional
import t4b_cleaners_prose


def continuous_t4b_text(work_id: str, text: str) -> str | None:
    """Return a vetted continuous reading text when one exists for a work."""
    if work_id.startswith("prdl-32287_"):
        return clean_prdl_32287_reading_text(text)
    for cleaner in (
        t4b_cleaners_prose.clean,
        t4b_cleaners_devotional.clean,
        t4b_cleaners_cipher.clean,
    ):
        cleaned = cleaner(work_id, text)
        if cleaned is not None:
            return cleaned
    return None


def load_t4b_works() -> list[dict]:
    """Load all 27 T4B works from works-t4b/."""
    works = []
    for meta_path in sorted(T4B_ROOT.glob("*/metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        works.append(meta)
    return works


def _reading_title(work_id: str) -> str:
    meta_path = T4B_ROOT / work_id / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta.get("title_en") or meta.get("title") or work_id


def _ensure_reading_title(markdown_text: str, title: str) -> str:
    first = re.match(r"^#{1,4}\s+(.+)$", markdown_text.strip(), re.M)
    normalized_title = re.sub(r"\W+", " ", title).strip().lower()
    normalized_first = re.sub(r"\W+", " ", first.group(1)).strip().lower() if first else ""
    if first and (normalized_title in normalized_first or normalized_first in normalized_title):
        return markdown_text
    return f"## {title}\n\n{markdown_text.lstrip()}"


def t4b_english_html(work_id: str) -> str:
    """Render the T4B english.md into HTML, segment by segment."""
    eng_path = T4B_ROOT / work_id / "english.md"
    if not eng_path.exists():
        return ""
    text = eng_path.read_text(encoding="utf-8", errors="replace")
    body = continuous_t4b_text(work_id, text)
    if body is not None:
        # Continuous editions are display-only transformations. The archival
        # page/chunk witnesses remain untouched in works-t4b.
        body = re.sub(r"(?i)\[Page\s+\d+\]", "", body)
        body = re.sub(r"(?mi)^.*urn:nbn:.*$", "", body)
        body = re.sub(r"(?mi)^(?:ROYAL LIBRARY(?: OF MUNICH)?|BIBLIOTHECA REGIA MONACENSIS)\.?\s*$", "", body)
        body = _ensure_reading_title(body, _reading_title(work_id))
        return (
            '<section class="segment reading-edition" id="reading-text">\n'
            f'{bs._chunk_markdown_to_html(body)}\n</section>'
        )
    # Split on [segment N] markers and render each chunk
    parts = re.split(r"\[segment (\d+)\]", text)
    blocks = []
    for i in range(1, len(parts), 2):
        seg = int(parts[i])
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        body = clean_t4b_body(body)
        if not body:
            continue
        blocks.append(f'<section class="segment" id="seg-{seg}">\n{bs._chunk_markdown_to_html(body) if hasattr(bs, "_chunk_markdown_to_html") else body}\n</section>')
    if not blocks:
        # fallback: render the whole thing
        return bs._chunk_markdown_to_html(text) if hasattr(bs, "_chunk_markdown_to_html") else f"<pre>{text}</pre>"
    if blocks:
        title = html.escape(_reading_title(work_id))
        blocks[0] = f'<h2 class="reading-work-title">{title}</h2>\n' + blocks[0]
    return "\n\n".join(blocks)


def t4b_chapters(work_id: str) -> dict | None:
    """Return chapter entries whose anchors exist in this T4B rendering."""
    english_path = T4B_ROOT / work_id / "english.md"
    if english_path.exists() and continuous_t4b_text(
        work_id, english_path.read_text(encoding="utf-8", errors="replace")
    ) is not None:
        # Continuous editions replace production-segment anchors with semantic
        # headings in one uninterrupted article.
        return None
    chapters = bs.load_chapters(work_id)
    if not chapters:
        return None
    text = (T4B_ROOT / work_id / "english.md").read_text(encoding="utf-8", errors="replace")
    segments = {int(n) for n in re.findall(r"\[segment (\d+)\]", text)}
    filtered = dict(chapters)
    filtered["entries"] = [entry for entry in chapters.get("entries", []) if entry.get("n") in segments]
    return filtered if len(filtered["entries"]) > 1 else None


def clean_t4b_body(text: str) -> str:
    """Hide scan-navigation clutter while retaining it in archival markdown."""
    text = re.sub(r"(?m)^\s*---\s*Page\s+\d+\s*---\s*$", "", text)
    text = re.sub(r"(?i)\[Page\s+\d+\]", "", text)
    text = re.sub(r"(?mi)^\s*\[(?:blank page|book cover; no translatable text\.)\]\s*$", "", text)
    text = re.sub(
        r"(?mi)^\s*\[(?:Digitization calibration target|Digitization color-calibration target|"
        r"OCR-damaged non-body page|OCR duplicate fragment|Duplicate scan leaves)[^\]]*\]\s*$",
        "", text,
    )
    text = re.sub(r"(?mi)^\s*(?:ROYAL LIBRARY OF MUNICH|Bavarian State Library|BSB Bayerische StaatsBibliothek)\.?\s*$", "", text)
    text = re.sub(
        r"(?mi)^\s*(?:ROYAL LIBRARY|OF MUNICH\.?|Herzog August (?:Library|Bibliothek)(?: [^\r\n]+)?|"
        r"Wolfenbüttel|Kodak|Gray Scale)\s*$",
        "", text,
    )
    text = re.sub(r"(?mi)^\s*©\s*\d{4}\s+digitalfoto-trainer\.de\s*$", "", text)
    text = re.sub(r"(?mi)^.*urn:nbn:.*$", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


_PRDL_32287_RUNNING_HEAD = re.compile(
    r"^(?:"
    r"To the [Rr]eader\.?|"
    r"(?:An? )?Apologetic(?:al)? [Dd]efen[cs]e\.?|"
    r"(?:The )?Steganograph(?:y|ia) of Trithemius\.?|"
    r"Trithemius[’']s Steganography\.?|"
    r"Questions?\.?|Of (?:the )?Questions\.?|"
    r"Fragment(?:um)?\.?|Fragment of (?:the )?Questions\.?"
    r")$",
    re.I,
)


def _prdl_32287_paragraphs(page_text: str, page: int) -> list[str]:
    """Return body paragraphs from one scan page, without printed furniture."""
    page_text = re.sub(r"(?m)^\[segment \d+\]\s*$", "", page_text)
    filtered_lines: list[str] = []
    for line in page_text.splitlines():
        stripped = line.strip()
        furniture_text = re.sub(r"^\d+\s+|\s+\d+$", "", stripped).strip()
        structural_line = (
            (page == 8 and stripped == "TO THE READER.") or
            (page == 12) or  # retain the multiline main title
            (page == 80 and stripped.startswith("FROM THE BOOK OF JOHANNES TRITHEMIUS"))
        )
        if not structural_line and (
            re.fullmatch(r"\d+", stripped) or
            _PRDL_32287_RUNNING_HEAD.fullmatch(furniture_text)
        ):
            continue
        filtered_lines.append(line)
    page_text = "\n".join(filtered_lines)
    paragraphs = [re.sub(r"[ \t]+", " ", p.strip())
                  for p in re.split(r"\n\s*\n", page_text) if p.strip()]
    cleaned: list[str] = []
    for paragraph in paragraphs:
        one_line = " ".join(paragraph.split())
        structural_title = (
            (page == 8 and one_line == "TO THE READER.") or
            (page == 12 and one_line.startswith("AN APOLOGETIC DEFENSE OF THE STEGANOGRAPHY")) or
            (page == 80 and one_line.startswith("FROM THE BOOK OF JOHANNES TRITHEMIUS"))
        )
        if not structural_title and _PRDL_32287_RUNNING_HEAD.fullmatch(one_line):
            continue
        if re.fullmatch(r"\d+", one_line):
            continue
        if re.fullmatch(r"[A-Z]?\s*\d+\s+[A-Z][A-Za-z-]*", one_line):
            continue
        if one_line in {"FRAG.", "FRAGMENT", "POWDER"}:
            continue
        cleaned.append(paragraph)
    return cleaned


def _prdl_32287_is_catchword(paragraph: str, following: str) -> bool:
    """Recognize a short catchword repeated at the head of the next page."""
    word = " ".join(paragraph.split()).strip(" .,:;")
    if not word or len(word.split()) > 3:
        return False
    next_words = " ".join(following.split()).lower()
    stem = word.rstrip("-").lower()
    if word.endswith("-"):
        return next_words.startswith(stem)
    return next_words == stem or next_words.startswith(stem + " ")


def clean_prdl_32287_reading_text(text: str) -> str:
    """Create a continuous, book-like reading text for the 1616 *Vindex*.

    The committed translation remains a page-faithful archival artifact.  This
    display transform removes only identifiable print/digitization furniture,
    joins page-turn interruptions, and adds a small semantic hierarchy.
    """
    marker = re.compile(r"(?m)^--- Page (\d+) ---\s*$")
    matches = list(marker.finditer(text))
    pages: list[tuple[int, list[str]]] = []
    for index, match in enumerate(matches):
        page = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        # Calibration leaves, terminal OCR failure, and blank/end leaves do not
        # belong in the clean reading stream.
        if page in {2, 3, 139, 140, 141}:
            continue
        paragraphs = _prdl_32287_paragraphs(text[start:end], page)
        if paragraphs:
            pages.append((page, paragraphs))

    joined: list[tuple[int, str]] = []
    for page, paragraphs in pages:
        if joined and paragraphs:
            previous = joined[-1][1]
            following = paragraphs[0]
            if _prdl_32287_is_catchword(previous, following):
                joined.pop()
            elif not re.search(r"[.!?…][\"”’']?$", previous.rstrip()):
                joined[-1] = (joined[-1][0], previous.rstrip("-") +
                              ("" if previous.endswith("-") else " ") + following.lstrip())
                paragraphs = paragraphs[1:]
        joined.extend((page, paragraph) for paragraph in paragraphs)

    output: list[str] = []
    for page, paragraph in joined:
        one_line = " ".join(paragraph.split())
        if page == 7 and one_line == "ON TRITHEMIUS, THE VINDICATOR OF HIMSELF AFTER DEATH.":
            output.append("## On *Trithemius, the Vindicator of Himself After Death*")
        elif page == 8 and one_line == "TO THE READER.":
            output.append("## To the Reader")
        elif page == 12 and one_line.startswith("AN APOLOGETIC DEFENSE OF THE STEGANOGRAPHY"):
            output.append("## An Apologetic Defense of the Steganography")
        elif page == 80 and one_line.startswith("FROM THE BOOK OF JOHANNES TRITHEMIUS"):
            output.append("## Fragment from Trithemius’s *Eight Questions to Emperor Maximilian*")
        elif page == 84 and one_line == "ON THE REPROBATE AND WITCHES.":
            output.append("### On the Reprobate and Witches")
        elif page == 98 and one_line.startswith("ON THE POWER OF WITCHES"):
            output.append("### On the Power of Witches\n\n#### Question Six")
        elif page == 114 and one_line == "ON DIVINE PERMISSION.":
            output.append("### On Divine Permission")
        elif re.fullmatch(r"Question (?:Five|Six|Seven)\.", one_line):
            output.append(f"#### {one_line.rstrip('.')}")
        elif one_line.startswith("The fifth question of your most serene Highness was this:"):
            output.append(f"#### Question Five\n\n{paragraph}")
        elif one_line == "Why God permits so many evils and acts of witchcraft.":
            output.append("#### Why God Permits So Many Evils and Acts of Witchcraft")
        elif page == 136 and one_line.startswith("A VERY CELEBRATED MEDICINAL POWDER"):
            output.append("## A Celebrated Medicinal Powder of Trithemius")
        else:
            output.append(paragraph)

    return "\n\n".join(output).strip()


def build_t4b_work_page(env, work: dict) -> str:
    """Render a single T4B work page using work.html.j2."""
    work_id = work["id"]
    work_dir = T4B_ROOT / work_id

    english_html = t4b_english_html(work_id)
    # T4B uses the same numbered source segments as the published witness, so
    # its existing chapter map can drive the floating chapter navigator too.
    chapters = t4b_chapters(work_id)
    chapters = bs.chapters_with_rendered_anchors(chapters, english_html, "seg")

    # intro
    intro_html = None
    intro_path = work_dir / "intro.md"
    if intro_path.exists():
        intro_html = bs.render_markdown_file(intro_path)

    # Build a work dict compatible with work.html.j2 expectations
    display_work = dict(work)
    display_work["genre"] = work.get("genre_cluster", "")
    display_work["genre_label"] = work.get("genre_cluster", "").replace("-", " ").title()
    display_work["fluent_adj"] = work.get("faithful_adj", 0)  # T4B doesn't have separate fluent grade
    display_work["is_primary"] = True
    bs.attach_public_status(display_work, edition_track="trithemius-4b")
    if any(work_id.startswith(prefix) for prefix in (
        "prdl-24389_", "prdl-24391_", "prdl-24395_",
        "prdl-70282_", "prdl-70291_", "prdl-70292_",
    )):
        display_work["editorial_state"] = "Structured diplomatic view"

    desc = f"Provisional machine-produced Trithemius 4B English reading text of {work.get('title_en') or work.get('title', work_id)} ({work.get('year', '')}), produced from a corpus-trained Qwen3-VL OCR witness and GPT-5.5 dual-context translation."

    return env.get_template("work.html.j2").render(
        work=display_work,
        intro=intro_html,
        english=english_html or None,
        has_parallel=False,
        style_c=None,
        chapters=chapters,
        chapter_anchor="seg",
        related=[],
        citation=bs.citation_text(display_work) if hasattr(bs, "citation_text") else "",
        work_id=work_id,
        work_title=work.get("title_en") or work.get("title") or work_id,
        reading_body_has_title=True,
        reading_time=None,
        has_errata=False,
        errata_html=None,
        prev_work=None,
        next_work=None,
        all_work_ids=[w["id"] for w in load_t4b_works()],
        solve=None,
        work_cover=None,
        url=bs.make_url(1),
        asset=bs.make_asset(1),
        **bs.page_meta(f"works/{work_id}-trithemius-4b.html", desc, nav="works"),
    )


def build_t4b_index(env, works: list[dict]) -> str:
    """Build an index page listing all 27 T4B editions."""
    from jinja2 import select_autoescape, Environment, FileSystemLoader
    # Use a simple inline template for the index
    rows = []
    for w in sorted(works, key=lambda x: (x.get("title_en") or x.get("title", x["id"]))):
        bs.attach_public_status(w, edition_track="trithemius-4b")
        rows.append({
            "id": w["id"],
            "title": w.get("title_en") or w.get("title", w["id"]),
            "editorial": w.get("editorial_state"),
            "review": w.get("human_review"),
            "qa": w.get("automated_qa"),
            "coverage": w.get("automated_qa_coverage", 0),
            "chunks": w.get("chunks_total", 0),
            "year": w.get("year", ""),
        })
    body_html = f"""
<h1>Trithemius 4B Editions</h1>
<p class="lede">Provisional machine-produced English reading texts for {len(works)} works, produced from a
corpus-trained <strong>Qwen3-VL-4B &ldquo;Trithemius&rdquo; LoRA</strong> OCR witness and
<strong>GPT-5.5 dual-context</strong> translation. Automated model audits are retained as
provenance and triage evidence; no text is presented as human-verified. The earlier machine
translations remain available as independent comparison editions.</p>
<table class="scoreboard">
<thead><tr><th>Work</th><th>Editorial state</th><th>Human review</th><th>Automated QA</th><th>Chunks</th></tr></thead>
<tbody>
"""
    for r in rows:
        body_html += (
            f'<tr><td><a href="works/{r["id"]}-trithemius-4b.html">{r["title"]}</a>'
            f' <span class="muted">({r["year"]})</span></td>'
            f'<td>{r["editorial"]}</td><td>{r["review"]}</td>'
            f'<td>{r["qa"]} ({r["coverage"]:.0f}%)</td><td>{r["chunks"]}</td></tr>\n'
        )
    body_html += "</tbody></table>"
    body_html += """
<p class="note">The Trithemius 4B LoRA was fine-tuned on this corpus&rsquo;s own
page/transcription pairs. Its OCR is the witness for this edition&rsquo;s Latin.
See <a href="methodology.html">Methodology</a> for the full OCR and translation
record, including the works that were tried and did not ship from this lane.</p>
"""
    return bs.render_simple_page(
        env,
        "Trithemius 4B Editions",
        body_html,
        "works-trithemius-4b.html",
        description="Provisional machine-produced English reading texts of 27 works, with explicit editorial and review status.",
        nav="works",
    )


def main() -> int:
    env = bs.make_env()
    works = load_t4b_works()
    if not works:
        print("No T4B works found in works-t4b/")
        return 1

    works_out = bs.OUT / "works"
    works_out.mkdir(exist_ok=True)

    print(f"Building {len(works)} Trithemius 4B edition pages...")
    for work in works:
        html = build_t4b_work_page(env, work)
        out_path = works_out / f"{work['id']}-trithemius-4b.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"  {work['id'][:40]}: reading page generated")

    # Index page
    index_html = build_t4b_index(env, works)
    (bs.OUT / "works-trithemius-4b.html").write_text(index_html, encoding="utf-8")

    # Inject "Trithemius 4B edition" links into the corresponding main work pages.
    link_t4b_into_main_pages(works)

    print(f"\nWrote {len(works)} T4B work pages + index to {works_out}/")
    return 0


def link_t4b_into_main_pages(t4b_works: list[dict]) -> None:
    """Add a 'Trithemius 4B edition' badge/link to each main work page that has a T4B edition."""
    works_out = bs.OUT / "works"
    linked = 0
    for tw in t4b_works:
        work_id = tw["id"]
        main_page = works_out / f"{work_id}.html"
        if not main_page.exists():
            continue
        html = main_page.read_text(encoding="utf-8")
        # Inject the T4B badge right after the parallel-viewer badge if present,
        # otherwise after the tier badge block. Use the T4B tier for the label.
        t4b_tier = tw.get("tier", "A")
        t4b_url = f"{work_id}-trithemius-4b.html"
        t4b_badge = (
            f'<a class="badge badge-t4b" href="{t4b_url}" '
            f'title="Recommended English edition: Qwen3-VL-4B Trithemius LoRA OCR + GPT-5.5, graded {t4b_tier} by Sonnet">'
            f'&#9733;&nbsp;Recommended:&nbsp;Trithemius&nbsp;4B&nbsp;edition&nbsp;({t4b_tier})</a>'
        )
        # Inject the T4B badge right before the closing </div> of the badges block.
        # The badges block ends with "viewer</a>  </div>" — insert before that </div>.
        marker = "&nbsp;viewer</a>  </div>"
        if marker in html and "badge-t4b" not in html:
            html = html.replace(marker, "&nbsp;viewer</a>" + t4b_badge + "  </div>", 1)
            main_page.write_text(html, encoding="utf-8")
            linked += 1
        else:
            # fallback: no parallel viewer badge, inject after the badges div open
            marker2 = '<div class="badges">'
            if marker2 in html and "badge-t4b" not in html:
                html = html.replace(marker2, marker2 + "\n" + t4b_badge, 1)
                main_page.write_text(html, encoding="utf-8")
                linked += 1
    print(f"  Linked T4B editions from {linked} main work pages")


if __name__ == "__main__":
    raise SystemExit(main())
