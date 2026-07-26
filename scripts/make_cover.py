"""Generate a designed typographic SVG cover for a work.

A period-flavoured title-page cover: double gilt rule frame, ornament, the
work title set in a classical serif, the edition + year, and the corpus
attribution. Rendered as inline SVG so it scales crisply and adds no image
weight. Used as the work-page hero and (rendered to PNG) as the og:image.

Usage as a module: build_cover_svg(work) -> str  (inline SVG for the page)
"""
import html
import re
import textwrap


# Ornament glyphs that read in most serif/system fonts. A composite printer's
# mark built from circles + fleurons rather than relying on one rare glyph.
ORNAMENT = (
    '<g class="orn" fill="none" stroke="currentColor" stroke-width="0.9">'
    '<circle cx="0" cy="0" r="6.5"/>'
    '<circle cx="0" cy="0" r="2.4" fill="currentColor" stroke="none"/>'
    '<path d="M -13 0 L -7 0 M 13 0 L 7 0 M 0 -13 L 0 -7 M 0 13 L 0 7"/>'
    '<path d="M -9.2 -9.2 L -5 -5 M 9.2 -9.2 L 5 -5 M -9.2 9.2 L -5 5 M 9.2 9.2 L 5 5" stroke-width="0.7"/>'
    '</g>'
)


def _clean_title(s: str) -> str:
    """Strip parenthetical edition/source annotations from a title so the
    cover shows the clean work name, e.g.
    'Polygraphiae libri VI (Basel: Furter & Petri, for Haselberg, 1518)'
    -> 'Polygraphiae libri VI'."""
    s = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # drop trailing edition noise like "first edition"
    s = re.sub(r",\s*(first|second|third|\d+\w*)\s+edition.*$", "", s, flags=re.I)
    return s.strip(" ,;:.")


def _wrap(title: str, max_chars: int) -> list[str]:
    """Wrap a long title into balanced lines for the cover."""
    title = re.sub(r"\s+", " ", title.strip())
    # Prefer breaking at punctuation, else on word boundaries
    lines = textwrap.wrap(title, width=max_chars, break_long_words=False,
                          break_on_hyphens=False)
    # cap at 4 lines
    if len(lines) > 4:
        # re-wrap tighter
        lines = textwrap.wrap(title, width=max_chars + 6,
                              break_long_words=False, break_on_hyphens=False)[:4]
    return lines or [title]


def _year_label(work: dict) -> str:
    """e.g. 'Basel, 1518' or 'Composed 1494 · Printed 1518'."""
    src_year = work.get("source_year") or work.get("year")
    comp_year = work.get("year")
    parts = []
    if comp_year and src_year and comp_year != src_year:
        parts.append(f"Composed {comp_year}")
        parts.append(f"Printed {src_year}")
        return " · ".join(parts)
    if src_year:
        return f"Printed {src_year}"
    if comp_year:
        return f"{comp_year}"
    return ""


def build_cover_svg(work: dict, *, width: int = 800) -> str:
    """Return inline SVG markup for the work's typographic cover."""
    title = _clean_title(work.get("title_en") or work.get("title") or "Untitled")
    # Several covers can be embedded on one browse page. SVG fragment IDs live
    # in the containing HTML document, so a generic ``cv-bg`` would be
    # duplicated and every rect could resolve to the first cover's gradient.
    work_key = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(work.get("id") or title)).strip("-")
    gradient_id = f"cv-bg-{work_key or 'work'}"
    # shorten very long titles but keep readable
    if len(title) > 90:
        title = title[:87].rstrip() + "…"
    latin_raw = _clean_title(work.get("title") or "")
    # show Latin subtitle only if it's meaningfully different from the English
    latin_short = latin_raw if latin_raw and latin_raw.lower() != title.lower() else ""
    if len(latin_short) > 120:
        latin_short = latin_short[:117].rstrip() + "…"
    year = _year_label(work)

    # 3:4 portrait ratio, like a book cover
    h = int(width * 4 / 3)

    # wrap title lines (rough char budget scaled to width)
    char_budget = max(22, int(width / 26))
    lines = _wrap(title, char_budget)

    # vertical layout maths — title block centred
    title_block_h = len(lines) * 52 + (40 if latin_short else 0)
    title_y0 = h // 2 - title_block_h // 2

    # build line tspans
    title_svg = []
    for i, ln in enumerate(lines):
        y = title_y0 + i * 52 + 40
        title_svg.append(
            f'<text x="50%" y="{y}" class="t" text-anchor="middle">{html.escape(ln)}</text>')
    if latin_short:
        ly = title_y0 + len(lines) * 52 + 70
        title_svg.append(
            f'<text x="50%" y="{ly}" class="lat" text-anchor="middle">{html.escape(latin_short)}</text>')

    # ornament above the title
    orn_y = title_y0 - 36
    # year + edition below the title
    foot_y = title_y0 + len(lines) * 52 + (110 if latin_short else 80)

    # Footer: prefer a substantive edition label (place/printer) over a bare
    # year when one exists, so we don't show "Printed 1518 · 1518". Long
    # colophon-style edition strings are shortened to place + year.
    edition = _clean_title(work.get("edition_info") or "")
    has_place = bool(re.search(r"[A-Za-z]{4,}", edition)) and edition != str(year or "")
    if has_place:
        foot = edition
        # shorten "Francofurti : Johann Berner; Balthasar Hofmann, 1608" -> "Francofurti, 1608"
        if len(foot) > 32:
            pm = re.match(r"([A-Za-z]+)", foot)
            yr = re.search(r"(1[4-6]\d{2})", foot)
            if pm and yr:
                foot = f"{pm.group(1)}, {yr.group(1)}"
            elif len(foot) > 40:
                foot = foot[:37].rstrip() + "…"
    else:
        foot = year

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {h}"
     role="img" aria-label="Cover: {html.escape(title)}"
     class="work-cover" preserveAspectRatio="xMidYMid meet">
  <defs>
    <linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1c1610"/>
      <stop offset="1" stop-color="#120d08"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{h}" fill="url(#{gradient_id})"/>
  <!-- double gilt rule frame -->
  <rect x="22" y="22" width="{width-44}" height="{h-44}" fill="none"
        stroke="#c9a24a" stroke-width="1.4" opacity="0.85"/>
  <rect x="30" y="30" width="{width-60}" height="{h-60}" fill="none"
        stroke="#c9a24a" stroke-width="0.6" opacity="0.6"/>
  <!-- corner accents -->
  <g fill="#c9a24a" opacity="0.7">
    <circle cx="30" cy="30" r="2.4"/><circle cx="{width-30}" cy="30" r="2.4"/>
    <circle cx="30" cy="{h-30}" r="2.4"/><circle cx="{width-30}" cy="{h-30}" r="2.4"/>
  </g>
  <!-- corpus attribution (top) -->
  <text x="50%" y="78" class="brand" text-anchor="middle" fill="#8a7a4a">
    JOHANNES TRITHEMIUS
  </text>
  <!-- ornament -->
  <g transform="translate({width//2}, {orn_y})" style="color:#c9a24a">
    {ORNAMENT}
  </g>
  <!-- title -->
  {''.join(title_svg)}
  <!-- footer: year + edition -->
  <text x="50%" y="{foot_y}" class="foot" text-anchor="middle" fill="#9a8456">
    {html.escape(foot)}
  </text>
  <text x="50%" y="{h-58}" class="brand2" text-anchor="middle" fill="#6a5c3a">
    TRITHEMIUS CORPUS
  </text>
  <style>
    .t {{ font: 600 34px Georgia, "Iowan Old Style", "Palatino Linotype", serif; fill: #e8dcc0; letter-spacing: 0.01em; }}
    .lat {{ font: italic 15px Georgia, "Palatino Linotype", serif; fill: #9a8456; }}
    .foot {{ font: 500 15px Georgia, serif; letter-spacing: 0.06em; }}
    .brand, .brand2 {{ font: 600 13px Georgia, serif; letter-spacing: 0.22em; }}
  </style>
</svg>'''


if __name__ == "__main__":
    # quick render test
    import json, sys
    from pathlib import Path
    from PIL import Image
    root = Path(__file__).resolve().parents[1]
    mf = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    works = [w for w in mf["works"] if not w.get("skip")]
    arg = sys.argv[1] if len(sys.argv) > 1 else works[0]["id"]
    w = next((x for x in works if x["id"].startswith(arg[:18])), works[0])
    svg = build_cover_svg(w)
    out = root / ".cache" / "cover_test.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out} for {w['id'][:30]}")
    print(f"svg size: {len(svg)} bytes")
