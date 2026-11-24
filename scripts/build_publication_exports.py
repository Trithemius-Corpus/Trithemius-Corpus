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
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import markdown
from edition_metadata import QA_LABELS, attribution, credit, editorial_record
from lxml import etree, html as lxml_html
from publication_guard import staged_directory


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "dist" / "editions"
SITE_BASE = "https://trithemius-corpus.github.io/Trithemius-Corpus/"
REPO_URL = "https://github.com/Trithemius-Corpus/Trithemius-Corpus"
CONTRIBUTOR = "Ian Carlos Fabin"
VERSION_SLOT = "\x00edition-version\x00"
MODIFIED_SLOT = "\x00edition-modified\x00"
NUMBER_SEQUENCE = re.compile(r"(?<![\w:])[0-9]+(?::[0-9]+){3,}(?![\w:])")
# Package this rule in editions that contain a wide table.
WIDE_TABLE_CSS = """
.wide-table { font-size: .65em; }
.wide-table th, .wide-table td { padding: .12em; }
"""


def checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_digest(files: dict[str, str]) -> str:
    """Hash named UTF-8 payloads independently of ZIP compression and OS."""
    members = {name: checksum(value) for name, value in files.items()}
    return checksum(json.dumps(members, sort_keys=True, separators=(",", ":")))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def export_context(root: Path) -> tuple[dict, str, str, str]:
    works = {w["id"]: w for w in load_json(root / "manifest.json")["works"] if not w.get("skip")}
    revisions = load_json(root / "data/publication/export-history.json")["format_revisions"]
    format_date = max(r["date"] for r in revisions)
    static = root / "site/static"
    print_css = (static / "publication.css").read_text(encoding="utf-8")
    epub_css = (static / "publication-epub.css").read_text(encoding="utf-8")
    return works, format_date, print_css, epub_css


def edition_source(root: Path, work: dict, format_date: str, css: str, epub_css: str) -> tuple[dict, str, str, str, str]:
    work_dir = root / "works" / work["id"]
    meta = load_json(work_dir / "metadata.json")
    if meta["id"] != work["id"]:
        raise ValueError(f"Work ID differs from the publication directory at {work_dir}")
    if work.get("title_en"):
        meta.setdefault("title_en", work["title_en"])
    intro = (work_dir / "intro.md").read_text(encoding="utf-8")
    english = strip_document_header((work_dir / "english.md").read_text(encoding="utf-8"))
    dates = [format_date]
    if meta.get("ai_corrections"):
        dates.append(meta["ai_corrections"]["date"])
    if meta.get("publication_modified"):
        dates.append(meta["publication_modified"])
    errata = work_dir / "ERRATA.md"
    if errata.is_file():
        dates.extend(re.findall(r"^#{1,6}\s+(\d{4}-\d{2}-\d{2})\b", errata.read_text(encoding="utf-8"), re.M))
    modified = max(datetime.strptime(day, "%Y-%m-%d") for day in dates).strftime("%Y-%m-%dT00:00:00Z")
    source_hash = content_digest({
        "metadata": json.dumps(meta, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
        "intro": intro, "english": english, "format revision": format_date,
        "print CSS": css, "epub CSS": epub_css,
    })
    return meta, intro, english, modified, source_hash


def modification_time(documented: str, prior: dict, fingerprint: str) -> str:
    """Retain an edition's recorded time on rebuild, including in a shallow checkout."""
    previous = prior.get("modified", "")
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        stamp = datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if stamp < documented:
            raise ValueError(f"SOURCE_DATE_EPOCH {stamp} predates the documented revision {documented}")
        return max(stamp, previous)
    if prior.get("content_sha256") and prior["content_sha256"] != fingerprint and documented <= previous:
        # First build of newly edited material with no newer dated erratum.
        # The index retains this date for subsequent identical builds.
        return max(previous, datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z"))
    return max(previous, documented)


def revision_version(label: str, modified: str, fingerprint: str) -> str:
    prefix = quote(label, safe="._+-") + "-" if label else ""
    return f"{prefix}{modified[:10]}.{fingerprint[:16]}"


def release_label(root: Path) -> str:
    override = os.environ.get("TRITHEMIUS_EDITION_VERSION", "").strip()
    citation = root / "CITATION.cff"
    if override or not citation.is_file():
        return override
    match = re.search(r"(?m)^version:\s*['\"]?([^'\"\s]+)", citation.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


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


def number_groups(sequence: str):
    """Keep whole numbers and their separators together at narrow reading widths."""
    group = ""
    for number in re.findall(r"[0-9]+:?", sequence):
        if group and len(group) + len(number) > 16:
            yield group
            group = ""
        group += number
    if group:
        yield group


def epub_reading_layout(markup: str) -> tuple[str, bool]:
    """Keep numeric prose and wide cipher tables readable on narrow EPUB pages."""
    if "<table" not in markup and not any(len(match[0]) >= 40 for match in NUMBER_SEQUENCE.finditer(markup)):
        return markup, False
    root = etree.fromstring(f"<div>{markup}</div>".encode("utf-8"))
    # Only rows with six or more actual cells need the compact formatting.
    wide_tables = root.xpath(".//table[tr[count(th|td) >= 6] or */tr[count(th|td) >= 6]]")
    for table in wide_tables:
        classes = table.get("class", "").split()
        if "wide-table" not in classes:
            table.set("class", " ".join([*classes, "wide-table"]))
    changed = bool(wide_tables)
    for text in root.xpath(".//p//text()"):
        matches = [match for match in NUMBER_SEQUENCE.finditer(text) if len(match[0]) >= 40]
        if not matches:
            continue
        # A text node can precede the paragraph's first child or follow inline markup.
        owner = text.getparent()
        if text.is_tail:
            container = owner.getparent()
            position = container.index(owner) + 1
            owner.tail = text[:matches[0].start()]
        else:
            container, position = owner, 0
            owner.text = text[:matches[0].start()]
        for i, match in enumerate(matches):
            for group in number_groups(match[0]):
                span = etree.Element("span", {"class": "number-run"})
                span.text = group
                container.insert(position, span)
                position += 1
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            span.tail = text[match.end():end]
        changed = True
    if not changed:
        return markup, False
    result = html.escape(root.text or "") + "".join(etree.tostring(child, encoding="unicode") for child in root)
    return result, bool(wide_tables)


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
    status = editorial_record(metadata, "earlier", {})
    return f'''<aside class="editorial-note" epub:type="notice" aria-labelledby="editorial-heading">
<h2 id="editorial-heading">Editorial status</h2>
<p>This is a machine-assisted English reading edition, not a critical edition. It may contain translation error, OCR damage, or unresolved text marked <span class="unclear">[unclear]</span>. Verify passages used in publication against the Latin transcription and the institutional facsimile.</p>
<p>{xml(QA_LABELS[status['automated_qa']])}. Coverage: {status['chunks_graded']} of {status['chunks_total']} source chunks. See the corpus methodology and work errata for the scope of review.</p>
</aside>'''


def provenance(metadata: dict, version: str) -> str:
    source = metadata.get("source") or {}
    source_url = source.get("url") or ""
    source_link = f'<a href="{xml(source_url)}">institutional source record</a>' if source_url else "institutional source record unavailable"
    alias_note = metadata.get("duplicate_source_note")
    shared_source = f"<dt>Source note</dt><dd>{xml(alias_note)}</dd>" if alias_note else ""
    work_url = f"{SITE_BASE}works/{metadata['id']}.html"
    corrections = metadata.get('ai_corrections')
    correction_note = (f'<p>Local AI scan-supported corrections: {xml(corrections["date"])}. Human review is not documented. Historical machine audits predate these edits; consult the work errata for the original wording and source evidence.</p>' if corrections else '')
    return f'''<section id="provenance" epub:type="colophon">
<h1>About this edition</h1>
<dl class="colophon-metadata">
<dt>Authorship</dt><dd>{xml(credit(metadata))}</dd>
<dt>Edition</dt><dd>{xml(metadata.get('edition_info', ''))}</dd>
<dt>English edition</dt><dd>{CONTRIBUTOR}, Trithemius Corpus {xml(version)}</dd>
<dt>Source</dt><dd>{source_link}</dd>{shared_source}
<dt>Canonical web edition</dt><dd><a class="canonical-url" href="{xml(work_url)}">{xml(work_url)}</a></dd>
<dt>License</dt><dd>CC0-1.0 for generated translation artifacts; see the repository license for documentation, code, and arrangement.</dd>
</dl>
{correction_note}
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
    authorship = attribution(metadata)
    roles = []
    if authorship.get("author"):
        roles.append(f'<dc:creator id="creator">{xml(authorship["author"])}</dc:creator><meta refines="#creator" property="role" scheme="marc:relators">aut</meta>')
    for key, role in (("transmitted_by", "oth"), ("attributed_to", "att")):
        if authorship.get(key):
            roles.append(f'<dc:contributor id="{key}">{xml(authorship[key])}</dc:contributor><meta refines="#{key}" property="role" scheme="marc:relators">{role}</meta>')
    if authorship.get("transmitted_by") or authorship.get("attributed_to"):
        roles.append(f"<dc:description>{xml(credit(metadata))}</dc:description>")
    work_id = metadata["id"]
    identifier = f"{REPO_URL}/works/{work_id}@{version}"
    title = metadata.get("title_en") or metadata.get("title") or work_id
    return f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="en">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/">
<dc:identifier id="pub-id">{xml(identifier)}</dc:identifier>
<dc:title id="title">{xml(title)}</dc:title><meta refines="#title" property="title-type">main</meta>
{''.join(roles)}
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
    info.create_system = 3
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
<p class="source-title" lang="la">{xml(source_title)}</p><p>{xml(credit(metadata))}</p><p>English edition by {CONTRIBUTOR}</p>
</header><main>
<section class="frontmatter" role="doc-preface"><h1>Introduction</h1>{intro_body}{caveat(metadata)}</section>
<article class="reading-text" role="doc-chapter"><h1>{xml(title)}</h1>{text_body}</article>
{provenance_body}</main></body></html>'''


def build_one(root: Path, out: Path, work: dict, format_date: str, css: str, epub_css: str,
              prior: dict, label: str) -> dict:
    metadata, intro, english, documented, source_hash = edition_source(root, work, format_date, css, epub_css)
    work_id = metadata["id"]
    title = metadata.get("title_en") or metadata.get("title") or work_id
    intro_body = markdown_xhtml(intro)
    text_body = markdown_xhtml(english)
    provenance_body = provenance(metadata, VERSION_SLOT)
    title_body = f'''<section class="title-page" epub:type="titlepage"><p class="series">Trithemius Corpus · Reading Edition {VERSION_SLOT}</p><h1>{xml(title)}</h1><p class="source-title" lang="la">{xml(metadata.get('title', title))}</p><p>{xml(credit(metadata))}</p><p>English edition by {CONTRIBUTOR}</p></section>'''
    intro_page = f'<section epub:type="preface"><h1>Introduction</h1>{intro_body}</section>{caveat(metadata)}'
    epub_body, has_wide_tables = epub_reading_layout(text_body)
    text_page = f'<article epub:type="bodymatter"><h1>{xml(title)}</h1>{epub_body}</article>'
    files = {
        "META-INF/container.xml": container_xml(),
        "EPUB/package.opf": package_document(metadata, VERSION_SLOT, MODIFIED_SLOT),
        "EPUB/nav.xhtml": navigation(title),
        "EPUB/publication.css": epub_css + (WIDE_TABLE_CSS if has_wide_tables else ""),
        "EPUB/titlepage.xhtml": xhtml_document(title, title_body, body_type="frontmatter"),
        "EPUB/introduction.xhtml": xhtml_document("Introduction", intro_page, body_type="frontmatter"),
        "EPUB/text.xhtml": xhtml_document(title, text_page),
        "EPUB/provenance.xhtml": xhtml_document("About this edition", provenance_body, body_type="backmatter"),
    }
    print_html = print_document(metadata, intro_body, text_body, provenance_body, VERSION_SLOT)
    print_html = re.sub(r"[ \t]+(?=\n)", "", print_html)
    fingerprint = content_digest({**files, "print/index.html": print_html, "print/publication.css": css})
    modified = modification_time(documented, prior, fingerprint)
    version = revision_version(label, modified, fingerprint)
    files = {path: value.replace(VERSION_SLOT, version).replace(MODIFIED_SLOT, modified) for path, value in files.items()}
    print_html = print_html.replace(VERSION_SLOT, version)
    epub_path = out / "epub" / f"{work_id}.epub"
    write_epub(epub_path, files)
    print_dir = out / "print" / work_id
    print_dir.mkdir(parents=True, exist_ok=True)
    (print_dir / "publication.css").write_text(css, encoding="utf-8", newline="\n")
    (print_dir / "index.html").write_text(print_html, encoding="utf-8", newline="\n")
    return {
        "id": work_id, "title": title, "edition_version": version, "release_label": label,
        "modified": modified, "identifier": f"{REPO_URL}/works/{work_id}@{version}",
        "content_sha256": fingerprint, "source_sha256": source_hash,
        "epub": f"epub/{work_id}.epub", "print": f"print/{work_id}/index.html",
        "epub_sha256": hashlib.sha256(epub_path.read_bytes()).hexdigest(),
        "print_sha256": checksum(print_html), "print_css_sha256": checksum(css),
        "source": metadata.get("source", {}).get("url", ""),
    }


def index_document(rows: list[dict]) -> dict:
    modified = max(row["modified"] for row in rows)
    fingerprint = content_digest({r["id"]: r["identifier"] for r in rows})
    return {"schema_version": "2.0", "edition_version": revision_version("", modified, fingerprint),
            "modified": modified, "works": rows}


def artifact_errors(out: Path, row: dict) -> list[str]:
    work_id = row["id"]
    epub = f"epub/{work_id}.epub"
    print_html = f"print/{work_id}/index.html"
    if (row.get("epub"), row.get("print")) != (epub, print_html):
        return [f"{work_id}: index paths differ from the canonical export paths"]
    errors = []
    for name, key in ((epub, "epub_sha256"), (print_html, "print_sha256"),
                      (f"print/{work_id}/publication.css", "print_css_sha256")):
        file = out / name
        if not file.is_file():
            errors.append(f"{work_id}: missing publication artifact {name}")
        elif row.get(key) != hashlib.sha256(file.read_bytes()).hexdigest():
            errors.append(f"{work_id}: {key} differs from {name}")
    return errors


def legacy_record(out: Path, row: dict) -> dict:
    """Index an untouched v1 artifact without claiming it contains the new edition."""
    work_id = row["id"]
    if row["print"] != f"print/{work_id}/index.html" or row["epub"] != f"epub/{work_id}.epub":
        raise ValueError(f"{work_id}: invalid legacy publication path")
    ns = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}
    with zipfile.ZipFile(out / row["epub"]) as archive:
        opf = etree.fromstring(archive.read("EPUB/package.opf"))
    identifier = opf.findtext(".//dc:identifier[@id='pub-id']", namespaces=ns)
    modified = opf.findtext(".//opf:meta[@property='dcterms:modified']", namespaces=ns)
    if not identifier or "@" not in identifier or not modified:
        raise ValueError(f"{work_id}: unrecognized legacy EPUB revision")
    print_file = out / row["print"]
    return {
        **row, "legacy": True, "edition_version": identifier.rsplit("@", 1)[1], "modified": modified,
        "identifier": identifier,
        "print_sha256": hashlib.sha256(print_file.read_bytes()).hexdigest(),
        "print_css_sha256": hashlib.sha256(print_file.with_name("publication.css").read_bytes()).hexdigest(),
    }


def inventory_errors(out: Path, rows: list[dict]) -> list[str]:
    expected = {"index.json"}
    for row in rows:
        work = row["id"]
        expected.update((f"epub/{work}.epub", f"print/{work}/index.html", f"print/{work}/publication.css"))
    actual = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    return [f"Missing publication file {name}" for name in sorted(expected - actual)] + [
        f"Unindexed publication file {name}" for name in sorted(actual - expected)]


def build_editions(work_ids: list[str] | None = None, *, out: Path | None = None, root: Path = ROOT) -> list[dict]:
    out = out if out is not None else root / "site/dist/editions"
    works, format_date, css, epub_css = export_context(root)
    label = release_label(root)
    selected = set(works if work_ids is None else work_ids)
    if not selected or selected - works.keys():
        raise ValueError(f"Expected publishable work IDs, got {sorted(selected - works.keys())}")
    lock = out.parent if out.resolve() == OUT.resolve() else out
    with staged_directory(out, seed=work_ids is not None, lock_target=lock) as stage:
        index_path = out / "index.json"
        old = load_json(index_path) if index_path.is_file() else {"works": []}
        prior = {r["id"]: r for r in old["works"]}
        if len(prior) != len(old["works"]) or prior.keys() - works.keys():
            raise ValueError("Export index contains repeated or unknown work IDs")
        records = dict(prior) if work_ids is not None else {}
        if work_ids is not None and prior and old.get("schema_version") != "2.0":
            for work_id in prior.keys() - selected:
                records[work_id] = legacy_record(stage, prior[work_id])
        for work_id in works:
            if work_id in selected:
                records[work_id] = build_one(root, stage, works[work_id], format_date, css, epub_css,
                                             prior.get(work_id, {}), label)
        rows = [records[work_id] for work_id in works if work_id in records]
        encoded = json.dumps(index_document(rows), ensure_ascii=False, indent=2) + "\n"
        (stage / "index.json").write_text(encoded, encoding="utf-8", newline="\n")
        errors = inventory_errors(stage, rows)
        for row in rows:
            errors.extend(artifact_errors(stage, row))
        if errors:
            raise ValueError("\n".join(errors))
    return [records[work_id] for work_id in works if work_id in selected]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", action="append", help="Build only this work id (repeatable)")
    args = parser.parse_args()
    try:
        records = build_editions(args.work)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Built {len(records)} EPUB 3.3 and paged-HTML edition(s) in {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
