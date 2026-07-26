"""Build deterministic EPUB 3.3 and paged-HTML reading editions.

The repository's canonical ``works/*/english.md`` files remain authoritative.
This exporter packages that text with its introduction, bibliographic metadata,
source provenance, and editorial caveats. PDF is intentionally a local release
artifact: Vivliostyle consumes the committed paged HTML and CSS.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import markdown
from lxml import etree, html as lxml_html


ROOT = Path(__file__).resolve().parents[1]
WORKS = ROOT / "works"
OUT = ROOT / "site" / "dist" / "editions"
CSS_SOURCE = ROOT / "site" / "static" / "publication.css"
EPUB_CSS_SOURCE = ROOT / "site" / "static" / "publication-epub.css"
SITE_BASE = "https://trithemius-corpus.github.io/Trithemius-Corpus/"
REPO_URL = "https://github.com/Trithemius-Corpus/Trithemius-Corpus"
CREATOR = "Johannes Trithemius"
CONTRIBUTOR = "Ian Carlos Fabin"


def publication_version() -> str:
    value = os.environ.get("TRITHEMIUS_EDITION_VERSION", "").strip()
    if value:
        return value
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"(?m)^version:\s*['\"]?([^'\"\s]+)", citation)
    if match:
        return match.group(1)
    released = re.search(r"(?m)^date-released:\s*['\"]?([^'\"\s]+)", citation)
    return released.group(1) if released else "development"


def modified_timestamp() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        moment = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    else:
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        released = re.search(r"(?m)^date-released:\s*['\"]?(\d{4}-\d{2}-\d{2})", citation)
        if released:
            return f"{released.group(1)}T00:00:00Z"
        # A date-only value keeps repeated builds on the same day identical.
        moment = datetime.now(timezone.utc)
    return moment.strftime("%Y-%m-%dT00:00:00Z")


def strip_document_header(text: str) -> str:
    """Remove the generated title/audit header already represented in metadata."""
    lines = text.replace("\r\n", "\n").splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].startswith("> Machine-assisted English translation"):
        lines.pop(0)
    while lines and (not lines[0].strip() or lines[0].strip() == "---"):
        lines.pop(0)
    return "\n".join(lines).strip() + "\n"


def markdown_xhtml(text: str) -> str:
    text = re.sub(r"<Addition>", '<span class="editorial-addition">', text, flags=re.I)
    text = re.sub(r"</Addition>", "</span>", text, flags=re.I)
    # OCR/cipher notation such as <k.s.13> is text, not an HTML custom element.
    text = re.sub(r"<([A-Za-z][^<>\s]*[.][^<>\s]*)>", lambda m: html.escape(m.group(0)), text)
    rendered = markdown.markdown(
        text,
        extensions=["extra", "sane_lists"],
        output_format="xhtml",
    )
    # EPUB is XML, so named HTML entities outside the XML five are unsafe.
    rendered = re.sub(
        r"&([A-Za-z][A-Za-z0-9]+);",
        lambda m: html.escape(html.unescape(m.group(0))),
        rendered,
    )
    # Source Markdown occasionally contains damaged raw table markup. Let the
    # HTML parser repair it, then serialize every fragment as well-formed XML.
    container = lxml_html.fragment_fromstring(rendered, create_parent="div")
    for link in container.iter("a"):
        href = link.get("href", "")
        if href and not (href.startswith(("#", "http://", "https://", "mailto:"))):
            link.set("href", SITE_BASE + href.lstrip("./"))
    pieces = [html.escape(container.text)] if container.text else []
    for child in container:
        pieces.append(etree.tostring(child, encoding="unicode", method="xml"))
    return "".join(pieces)


def xml(value: object) -> str:
    return html.escape(str(value), quote=True)


def xhtml_document(title: str, body: str, *, body_type: str = "bodymatter") -> str:
    return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en">
<head><meta charset="utf-8"/><title>{xml(title)}</title><link rel="stylesheet" href="publication.css"/></head>
<body epub:type="{body_type}">{body}</body>
</html>
'''


def caveat(metadata: dict) -> str:
    work_id = metadata["id"]
    return f'''<aside class="editorial-note" epub:type="notice" aria-labelledby="editorial-heading">
<h2 id="editorial-heading">Editorial status</h2>
<p>This is a machine-assisted English reading edition, not a critical edition. It may contain translation error, OCR damage, or unresolved text marked <span class="unclear">[unclear]</span>. Verify passages used in publication against the Latin transcription and the institutional facsimile.</p>
<p>Work identifier: <code>{xml(work_id)}</code>. Translation tier {xml(metadata.get('tier', ''))}; audited faithfulness {xml(metadata.get('faithful_adj', ''))}. See the corpus methodology and errata for scope and limitations.</p>
</aside>'''


def provenance(metadata: dict, version: str) -> str:
    source = metadata.get("source") or {}
    source_url = source.get("url") or ""
    source_link = f'<a href="{xml(source_url)}">institutional source record</a>' if source_url else "institutional source record unavailable"
    work_url = f"{SITE_BASE}works/{metadata['id']}.html"
    return f'''<section id="provenance" epub:type="colophon">
<h1>About this edition</h1>
<dl>
<dt>Author</dt><dd>{CREATOR}</dd>
<dt>Edition</dt><dd>{xml(metadata.get('edition_info', ''))}</dd>
<dt>English edition</dt><dd>{CONTRIBUTOR}, Trithemius Corpus {xml(version)}</dd>
<dt>Source</dt><dd>{source_link}</dd>
<dt>Canonical web edition</dt><dd><a href="{xml(work_url)}">{xml(work_url)}</a></dd>
<dt>License</dt><dd>CC0-1.0 for generated translation artifacts; see the repository license for documentation, code, and arrangement.</dd>
</dl>
<p>This export was generated from the canonical repository source. Stable passage-level citation is available in the web and TEI editions where passage identifiers have been assigned.</p>
<p><a href="{REPO_URL}/blob/main/METHODOLOGY.md">Methodology and limitations</a> · <a href="{REPO_URL}/blob/main/works/{xml(metadata['id'])}/ERRATA.md">Work errata</a></p>
</section>'''


def navigation(title: str) -> str:
    body = f'''<nav epub:type="toc" id="toc" role="doc-toc"><h1>Contents</h1><ol>
<li><a href="titlepage.xhtml">{xml(title)}</a></li>
<li><a href="introduction.xhtml">Introduction and editorial notice</a></li>
<li><a href="text.xhtml">English reading text</a></li>
<li><a href="provenance.xhtml">About this edition</a></li>
</ol></nav>
<nav epub:type="landmarks" hidden="hidden"><h2>Landmarks</h2><ol>
<li><a epub:type="cover" href="titlepage.xhtml">Title page</a></li>
<li><a epub:type="bodymatter" href="text.xhtml">English reading text</a></li>
<li><a epub:type="colophon" href="provenance.xhtml">About this edition</a></li>
</ol></nav>'''
    return xhtml_document("Contents", body, body_type="frontmatter")


def package_document(metadata: dict, version: str, modified: str) -> str:
    work_id = metadata["id"]
    identifier = f"{REPO_URL}/works/{work_id}@{version}"
    title = metadata.get("title_en") or metadata.get("title") or work_id
    return f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="en">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/">
<dc:identifier id="pub-id">{xml(identifier)}</dc:identifier>
<dc:title id="title">{xml(title)}</dc:title><meta refines="#title" property="title-type">main</meta>
<dc:creator id="creator">{CREATOR}</dc:creator><meta refines="#creator" property="role" scheme="marc:relators">aut</meta>
<dc:contributor id="contributor">{CONTRIBUTOR}</dc:contributor><meta refines="#contributor" property="role" scheme="marc:relators">trl</meta>
<dc:language>en</dc:language><dc:subject>Johannes Trithemius</dc:subject>
<dc:publisher>Trithemius Corpus</dc:publisher><dc:rights>CC0-1.0 translation artifacts; see LICENSE</dc:rights>
<meta property="dcterms:modified">{modified}</meta>
<meta property="schema:accessMode">textual</meta>
<meta property="schema:accessModeSufficient">textual</meta>
<meta property="schema:accessibilityFeature">structuralNavigation</meta>
<meta property="schema:accessibilityFeature">tableOfContents</meta>
<meta property="schema:accessibilityFeature">readingOrder</meta>
<meta property="schema:accessibilityHazard">none</meta>
<meta property="schema:accessibilitySummary">Reflowable English text with structural navigation. Cipher tables may require horizontal navigation at large text sizes; damaged source readings remain explicitly marked.</meta>
</metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="css" href="publication.css" media-type="text/css"/>
<item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>
<item id="introduction" href="introduction.xhtml" media-type="application/xhtml+xml"/>
<item id="text" href="text.xhtml" media-type="application/xhtml+xml"/>
<item id="provenance" href="provenance.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="titlepage"/><itemref idref="introduction"/><itemref idref="text"/><itemref idref="provenance"/></spine>
</package>
'''


def container_xml() -> str:
    return '''<?xml version="1.0" encoding="utf-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
<rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
'''


def zip_info(name: str, *, stored: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def write_epub(path: Path, files: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(zip_info("mimetype", stored=True), "application/epub+zip")
        for name in sorted(files):
            archive.writestr(zip_info(name), files[name].encode("utf-8"))


def print_document(metadata: dict, intro_body: str, text_body: str, provenance_body: str, version: str) -> str:
    title = metadata.get("title_en") or metadata.get("title") or metadata["id"]
    source_title = metadata.get("title") or title
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{xml(title)} — Trithemius Corpus</title><link rel="stylesheet" href="publication.css"></head>
<body class="publication" data-pagefind-ignore><header class="title-page" role="doc-cover">
<p class="series">Trithemius Corpus · Reading Edition {xml(version)}</p><h1>{xml(title)}</h1>
<p class="source-title" lang="la">{xml(source_title)}</p><p>Johannes Trithemius</p><p>English edition by {CONTRIBUTOR}</p>
</header><main>
<section class="frontmatter" role="doc-preface"><h1>Introduction</h1>{intro_body}{caveat(metadata)}</section>
<article class="reading-text" role="doc-chapter"><h1>{xml(title)}</h1>{text_body}</article>
{provenance_body}</main></body></html>'''


def build_one(work_dir: Path, css: str, epub_css: str, version: str, modified: str) -> dict:
    metadata = json.loads((work_dir / "metadata.json").read_text(encoding="utf-8"))
    title = metadata.get("title_en") or metadata.get("title") or metadata["id"]
    intro = (work_dir / "intro.md").read_text(encoding="utf-8", errors="replace")
    english = strip_document_header((work_dir / "english.md").read_text(encoding="utf-8", errors="replace"))
    intro_body = markdown_xhtml(intro)
    text_body = markdown_xhtml(english)
    provenance_body = provenance(metadata, version)
    title_body = f'''<section class="title-page" epub:type="titlepage"><p class="series">Trithemius Corpus · Reading Edition {xml(version)}</p><h1>{xml(title)}</h1><p class="source-title" lang="la">{xml(metadata.get('title', title))}</p><p>{CREATOR}</p><p>English edition by {CONTRIBUTOR}</p></section>'''
    intro_page = f'<section epub:type="preface"><h1>Introduction</h1>{intro_body}</section>{caveat(metadata)}'
    text_page = f'<article epub:type="bodymatter"><h1>{xml(title)}</h1>{text_body}</article>'
    files = {
        "META-INF/container.xml": container_xml(),
        "EPUB/package.opf": package_document(metadata, version, modified),
        "EPUB/nav.xhtml": navigation(title),
        "EPUB/publication.css": epub_css,
        "EPUB/titlepage.xhtml": xhtml_document(title, title_body, body_type="frontmatter"),
        "EPUB/introduction.xhtml": xhtml_document("Introduction", intro_page, body_type="frontmatter"),
        "EPUB/text.xhtml": xhtml_document(title, text_page),
        "EPUB/provenance.xhtml": xhtml_document("About this edition", provenance_body, body_type="backmatter"),
    }
    epub_path = OUT / "epub" / f"{metadata['id']}.epub"
    write_epub(epub_path, files)
    print_dir = OUT / "print" / metadata["id"]
    print_dir.mkdir(parents=True, exist_ok=True)
    (print_dir / "publication.css").write_text(css, encoding="utf-8", newline="\n")
    print_html = print_document(metadata, intro_body, text_body, provenance_body, version)
    print_html = re.sub(r"[ \t]+(?=\n)", "", print_html)
    (print_dir / "index.html").write_text(
        print_html,
        encoding="utf-8", newline="\n",
    )
    return {
        "id": metadata["id"], "title": title,
        "epub": f"epub/{metadata['id']}.epub",
        "print": f"print/{metadata['id']}/index.html",
        "epub_sha256": hashlib.sha256(epub_path.read_bytes()).hexdigest(),
        "source": metadata.get("source", {}).get("url", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", action="append", help="Build only this work id (repeatable)")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    publishable = [w["id"] for w in manifest["works"] if not w.get("skip")]
    selected = args.work or publishable
    unknown = sorted(set(selected) - set(publishable))
    if unknown:
        parser.error(f"not a publishable work: {', '.join(unknown)}")
    if not args.work and OUT.exists():
        shutil.rmtree(OUT)
    css = CSS_SOURCE.read_text(encoding="utf-8")
    epub_css = EPUB_CSS_SOURCE.read_text(encoding="utf-8")
    version = publication_version()
    modified = modified_timestamp()
    records = [build_one(WORKS / work_id, css, epub_css, version, modified) for work_id in selected]
    if not args.work:
        index = {"schema_version": "1.0", "edition_version": version, "modified": modified, "works": records}
        (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Built {len(records)} EPUB 3.3 and paged-HTML edition(s) in {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
