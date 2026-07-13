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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
T4B_ROOT = ROOT / "works-t4b"

# Import helpers from build_site (same module dir)
import build_site as bs  # noqa: E402


def load_t4b_works() -> list[dict]:
    """Load all 27 T4B works from works-t4b/."""
    works = []
    for meta_path in sorted(T4B_ROOT.glob("*/metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        works.append(meta)
    return works


def t4b_english_html(work_id: str) -> str:
    """Render the T4B english.md into HTML, segment by segment."""
    eng_path = T4B_ROOT / work_id / "english.md"
    if not eng_path.exists():
        return ""
    text = eng_path.read_text(encoding="utf-8", errors="replace")
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
    return "\n\n".join(blocks)


def t4b_chapters(work_id: str) -> dict | None:
    """Return chapter entries whose anchors exist in this T4B rendering."""
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
    text = re.sub(r"(?m)^\s*\[Page\s+\d+\]\s*$", "", text)
    text = re.sub(r"(?mi)^\s*\[(?:blank page|book cover; no translatable text\.)\]\s*$", "", text)
    text = re.sub(
        r"(?mi)^\s*\[(?:Digitization calibration target|Digitization color-calibration target|"
        r"OCR-damaged non-body page|OCR duplicate fragment|Duplicate scan leaves)[^\]]*\]\s*$",
        "", text,
    )
    text = re.sub(r"(?mi)^\s*(?:ROYAL LIBRARY OF MUNICH|Bavarian State Library|BSB Bayerische StaatsBibliothek)\.?\s*$", "", text)
    text = re.sub(r"(?mi)^\s*©\s*\d{4}\s+digitalfoto-trainer\.de\s*$", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def build_t4b_work_page(env, work: dict) -> str:
    """Render a single T4B work page using work.html.j2."""
    work_id = work["id"]
    work_dir = T4B_ROOT / work_id

    english_html = t4b_english_html(work_id)
    # T4B uses the same numbered source segments as the published witness, so
    # its existing chapter map can drive the floating chapter navigator too.
    chapters = t4b_chapters(work_id)

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

    desc = f"Recommended Trithemius 4B English edition of {work.get('title_en') or work.get('title', work_id)} ({work.get('year', '')}), produced from a corpus-trained Qwen3-VL OCR witness and GPT-5.5 dual-context translation. Graded {work.get('tier', '?')} by Claude Sonnet 5."

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
    for w in sorted(works, key=lambda x: -x.get("faithful_adj", 0)):
        rows.append({
            "id": w["id"],
            "title": w.get("title_en") or w.get("title", w["id"]),
            "tier": w.get("tier", "?"),
            "faith": w.get("faithful_adj", 0),
            "hall": w.get("hallucinated_pct", 0),
            "chunks": w.get("chunks_total", 0),
            "year": w.get("year", ""),
        })
    body_html = f"""
<h1>Trithemius 4B Editions</h1>
<p class="lede">The recommended English reading editions for {len(works)} works, produced from a
corpus-trained <strong>Qwen3-VL-4B &ldquo;Trithemius&rdquo; LoRA</strong> OCR witness and
<strong>GPT-5.5 dual-context</strong> translation. Independently graded by <strong>Claude Sonnet 5</strong>
(all works grade S or A). The earlier published translations remain available as independent
comparison editions.</p>
<table class="scoreboard">
<thead><tr><th>Work</th><th>Tier</th><th>Faith</th><th>Hall%</th><th>Chunks</th></tr></thead>
<tbody>
"""
    for r in rows:
        body_html += (
            f'<tr><td><a href="works/{r["id"]}-trithemius-4b.html">{r["title"]}</a>'
            f' <span class="muted">({r["year"]})</span></td>'
            f'<td><span class="badge tier-{r["tier"].lower()}">{r["tier"]}</span></td>'
            f'<td>{r["faith"]:.2f}</td><td>{r["hall"]:.1f}%</td><td>{r["chunks"]}</td></tr>\n'
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
        description="Recommended English editions of 27 works, translated from a corpus-trained Qwen3-VL LoRA OCR witness by GPT-5.5 and independently graded S/A by Claude Sonnet 5.",
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
        print(f"  {work['id'][:40]}: {work.get('tier')} {work.get('faithful_adj')}")

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
