"""Check editorial claims, complete introductions, rights, and known dates."""
from __future__ import annotations

import html
import json
import re

import build_site as bs


def plain(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", text)).split())


def main() -> int:
    errors: list[str] = []
    survey = bs.load_first_english()
    for wid, row in survey.items():
        if row.get('status') not in {'complete_prior','partial_prior','none_located','unresolved'}:
            errors.append(f'{wid}: missing/invalid survey classification')
        if row.get('first_english') != (row.get('status') in {'partial_prior','none_located'}):
            errors.append(f'{wid}: survey flag disagrees with classification')
    for wid, row in survey.items():
        if wid.startswith(('prdl-24389_','prdl-24390_','prdl-24391_')) and row.get('status') != 'partial_prior':
            errors.append(f'{wid}: partial Polygraphia translation is misclassified')
        if 'octo-quaestionum' in wid and row['status'] != 'partial_prior':
            errors.append(f'{wid}: the survey records English excerpts of the Eight Questions')
        if wid.startswith(('prdl-24376_','prdl-70281_','prdl-70282_','prdl-24383_')) and row.get('status') != 'unresolved':
            errors.append(f'{wid}: incomplete exact-work survey must remain unresolved')
    count = 0
    metadata_by_page = {}
    for root, suffix in (("works", ""), ("works-t4b", "-trithemius-4b")):
        for src in sorted((bs.ROOT / root).glob("*/intro.md")):
            page = bs.OUT / "works" / (src.parent.name + suffix + ".html")
            if not page.exists():
                errors.append(f"missing work page: {page.name}")
                continue
            rendered = page.read_text(encoding="utf-8")
            metadata_by_page[page.name] = json.loads(src.with_name("metadata.json").read_text(encoding="utf-8"))
            match = re.search(r'<section class="work-intro"[^>]*>\s*<h2\b[^>]*>About this work</h2>\s*(.*?)\s*</section>', rendered, re.S)
            expected = bs.render_markdown_file(src)
            if not match or match[1].strip() != bs.render_headnote(src).strip():
                errors.append(f"{page.name}: stale introduction")
            if re.search(r"top tier|audit tier|first freely accessible|first open,", expected, re.I):
                errors.append(f"{src.relative_to(bs.ROOT)}: obsolete editorial claim")
            for paragraph in re.findall(r"<p\b[^>]*>(.*?)</p>", expected, re.S):
                text = plain(paragraph)
                if re.search(r"\b(?:and|but|or|the|this|its|with)\s*[.;]?$|[,;:]$", text, re.I):
                    errors.append(f"{page.name}: incomplete introductory paragraph: {text[-90:]}")
            header = re.search(r'<header class="work-header">(.*?)</header>', rendered, re.S)
            if header and re.search(r"recommended|graded . by|\([SABCF]\)", plain(header[1]), re.I):
                errors.append(f"{page.name}: grade-based recommendation in header")
            if re.search(r'class="badge first-en"[^>]*>first English<', rendered):
                errors.append(f"{page.name}: unqualified first-English badge")
            count += 1

    for name in ("index.html", "works.html"):
        text = (bs.OUT / name).read_text(encoding="utf-8")
        if "prior-translations.html" not in text or re.search(r"in English for the first time|with no\s+English edition", text):
            errors.append(f"{name}: missing qualified translation survey link")
    home = (bs.OUT / "index.html").read_text(encoding="utf-8")
    for label, pattern in (("homepage", r'<p class="hero-byline muted">(.*?)</p>'),
                           ("footer", r'<p class="footer-byline muted">(.*?)</p>')):
        match = re.search(pattern, home, re.S)
        if not match or not all(x in plain(match[1]) for x in ("Translations & generated data: CC0", "CC BY 4.0")):
            errors.append(f"{label}: inconsistent rights summary")

    wid = "prdl-24362_de-laude-scriptorum-manualium"
    manifest_work = next(w for w in bs.load_manifest()["works"] if w["id"] == wid)
    for label, meta in [("manifest", manifest_work)] + [
        (root, json.loads((bs.ROOT / root / wid / "metadata.json").read_text(encoding="utf-8")))
        for root in ("works", "works-t4b")
    ]:
        if meta.get("composition_year") != "1492" or meta.get("year") != "1492" or meta.get("source_year") != "1494" or not meta.get("year_note"):
            errors.append(f"{label}: Scribes composition and witness dates are inconsistent")
    for suffix in ("", "-trithemius-4b"):
        page = (bs.OUT / "works" / f"{wid}{suffix}.html").read_text(encoding="utf-8")
        for row in ("<th>Composed</th><td>1492</td>", "<th>Edition (this witness)</th><td>1494</td>"):
            if row not in page:
                errors.append(f"Scribes{suffix}: missing distinct date row")
    for page in (bs.OUT / "works").glob("*.html"):
        for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page.read_text(encoding="utf-8"), re.S):
            data = json.loads(raw)
            if data.get("@type") == "Book" and data.get("license") != "https://creativecommons.org/publicdomain/zero/1.0/":
                errors.append(f"{page.name}: translation JSON-LD license is not CC0")
            if data.get("@type") == "Book":
                work = metadata_by_page.get(page.name, {})
                if data.get("dateCreated") != work.get("composition_year"):
                    errors.append(f"{page.name}: creation date is not supported by composition metadata")
    for root, suffix in (("works", ""), ("works-t4b", "-trithemius-4b")):
        for source in (bs.ROOT / root).glob("*/metadata.json"):
            meta = json.loads(source.read_text(encoding="utf-8"))
            page = bs.OUT / "works" / f"{meta['id']}{suffix}.html"
            if page.exists() and not meta.get("composition_year") and "<th>Composed</th>" in page.read_text(encoding="utf-8"):
                errors.append(f"{page.name}: generic year is mislabeled as composition")

    if errors:
        print("Editorial copy validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Editorial copy validation passed: {count} introductions, survey claims, rights, and Scribes dates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
