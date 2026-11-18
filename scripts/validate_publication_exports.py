"""Validate committed EPUB and paged-HTML publication exports."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from lxml import html

from build_publication_exports import (
    MODIFIED_SLOT, REPO_URL, VERSION_SLOT, artifact_errors, content_digest, edition_source,
    export_context, index_document, inventory_errors, revision_version,
)
from edition_metadata import attribution, credit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "dist" / "editions"
EPUB_NS = {"opf": "http://www.idpf.org/2007/opf", "x": "http://www.w3.org/1999/xhtml", "dc": "http://purl.org/dc/elements/1.1/"}
REQUIRED_CAVEAT = "This is a machine-assisted English reading edition, not a critical edition."


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_revision(package: ET.Element, row: dict, meta: dict, errors: list[str]) -> None:
    key = row["id"]
    def value(xpath: str) -> str | None:
        return package.findtext(xpath, namespaces=EPUB_NS)
    unique_id = package.get("unique-identifier")
    identifier = value(".//dc:identifier[@id='pub-id']")
    if unique_id != "pub-id" or identifier != row["identifier"] or identifier != f"{REPO_URL}/works/{key}@{row['edition_version']}":
        fail(errors, f"{key}: package identifier differs from the indexed edition")
    if value(".//opf:meta[@property='dcterms:modified']") != row["modified"]:
        fail(errors, f"{key}: package modification time differs from the indexed edition")
    if value(".//dc:title") != row["title"]:
        fail(errors, f"{key}: package title differs from the indexed edition")
    authorship = attribution(meta)
    author = authorship.get("author")
    creators = [item.text for item in package.findall(".//dc:creator", EPUB_NS)]
    if creators != ([author] if author else []):
        fail(errors, f"{key}: creator does not match the work attribution")
    if author and value(".//opf:meta[@refines='#creator'][@property='role'][@scheme='marc:relators']") != "aut":
        fail(errors, f"{key}: named author lacks the author role")
    for field, role in (("transmitted_by", "oth"), ("attributed_to", "att")):
        if value(f".//dc:contributor[@id='{field}']") != authorship.get(field):
            fail(errors, f"{key}: incorrect {field} contributor")
        if authorship.get(field):
            recorded_role = value(f".//opf:meta[@refines='#{field}'][@property='role'][@scheme='marc:relators']")
            if recorded_role != role or value(".//dc:description") != credit(meta):
                fail(errors, f"{key}: source role {field} is missing or incorrect")


def validate_epub(path: Path, row: dict, meta: dict, print_source: str, print_css: str, errors: list[str]) -> None:
    work_id = row["id"]
    try:
        with path.open("rb") as stream:
            if stream.read(4) != b"PK\x03\x04":
                fail(errors, f"{work_id}: EPUB is not a ZIP package")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if not names or names[0] != "mimetype":
                fail(errors, f"{work_id}: mimetype is not the first ZIP member")
            mime = archive.getinfo("mimetype")
            if mime.compress_type != zipfile.ZIP_STORED:
                fail(errors, f"{work_id}: mimetype member is compressed")
            if archive.read("mimetype") != b"application/epub+zip":
                fail(errors, f"{work_id}: invalid EPUB mimetype")
            required = {
                "META-INF/container.xml", "EPUB/package.opf", "EPUB/nav.xhtml",
                "EPUB/publication.css", "EPUB/titlepage.xhtml",
                "EPUB/introduction.xhtml", "EPUB/text.xhtml", "EPUB/provenance.xhtml",
            }
            missing = required - set(names)
            if missing:
                fail(errors, f"{work_id}: missing package members {sorted(missing)}")
                return
            parsed: dict[str, ET.Element] = {}
            for name in sorted(required - {"EPUB/publication.css"}):
                try:
                    parsed[name] = ET.fromstring(archive.read(name))
                except ET.ParseError as exc:
                    fail(errors, f"{work_id}: {name} is not well-formed XML: {exc}")
            package = parsed.get("EPUB/package.opf")
            if package is None:
                return
            if package.attrib.get("version") != "3.0":
                fail(errors, f"{work_id}: OPF package version is not EPUB 3")
            validate_revision(package, row, meta, errors)
            text = archive.read("EPUB/introduction.xhtml").decode("utf-8")
            if REQUIRED_CAVEAT not in text:
                fail(errors, f"{work_id}: EPUB lacks the required editorial caveat")
            provenance = archive.read("EPUB/provenance.xhtml").decode("utf-8")
            if "institutional source record" not in provenance or "Methodology and limitations" not in provenance:
                fail(errors, f"{work_id}: EPUB provenance links are incomplete")
            for name in ("EPUB/titlepage.xhtml", "EPUB/provenance.xhtml"):
                page = parsed.get(name)
                if page is not None and credit(meta) not in "".join(page.itertext()):
                    fail(errors, f"{work_id}: incorrect authorship in {name}")
            nav = parsed.get("EPUB/nav.xhtml")
            if nav is not None:
                nav_types = {el.attrib.get("{http://www.idpf.org/2007/ops}type") for el in nav.findall(".//x:nav", EPUB_NS)}
                if not {"toc", "landmarks"}.issubset(nav_types):
                    fail(errors, f"{work_id}: navigation lacks toc or landmarks")
            opf_text = archive.read("EPUB/package.opf").decode("utf-8")
            for token in ["schema:accessMode", "schema:accessibilityFeature", "schema:accessibilityHazard", "dc:language"]:
                if token not in opf_text:
                    fail(errors, f"{work_id}: package metadata lacks {token}")
            # Independently recover the unversioned payloads from the named files.
            # A matching file SHA alone would allow a stale edition ID to be retained.
            members = {n: archive.read(n).decode("utf-8") for n in names if n != "mimetype"}
            members["print/index.html"] = print_source
            members["print/publication.css"] = print_css
            for n in ("EPUB/package.opf", "EPUB/provenance.xhtml", "EPUB/titlepage.xhtml", "print/index.html"):
                members[n] = members[n].replace(row["edition_version"], VERSION_SLOT)
            members["EPUB/package.opf"] = members["EPUB/package.opf"].replace(
                f'property="dcterms:modified">{row["modified"]}', f'property="dcterms:modified">{MODIFIED_SLOT}')
            if content_digest(members) != row["content_sha256"]:
                fail(errors, f"{work_id}: revision fingerprint differs from the packaged content")
    except (OSError, KeyError, UnicodeError, zipfile.BadZipFile) as exc:
        fail(errors, f"{work_id}: unreadable EPUB: {exc}")


def run_epubcheck(paths: list[Path], command: str, errors: list[str]) -> None:
    for path in paths:
        proc = subprocess.run([command, str(path)], text=True, capture_output=True, check=False)
        if proc.returncode:
            output = (proc.stdout + proc.stderr).strip()
            fail(errors, f"{path.name}: EPUBCheck failed\n{output}")


def validate_exports(root: Path, out: Path, work_ids: list[str] | None = None) -> list[str]:
    errors: list[str] = []
    works, format_date, css, epub_css = export_context(root)
    selected = work_ids if work_ids is not None else list(works)
    index_path = out / "index.json"
    if not index_path.exists():
        return ["missing editions/index.json"]
    index = json.loads(index_path.read_text(encoding="utf-8"))
    rows = index.get("works", [])
    indexed = {r.get("id"): r for r in rows}
    if len(indexed) != len(rows) or indexed.keys() - works.keys():
        return ["Edition index contains duplicate or unknown work IDs"]
    if work_ids is None and indexed.keys() != works.keys():
        fail(errors, f"Edition index differs from {len(works)} publishable works")
    if list(indexed) != [key for key in works if key in indexed]:
        fail(errors, "Edition index order differs from the corpus manifest")
    if not rows or index.get("schema_version") != "2.0":
        return [*errors, "Empty or outdated edition index"]
    try:
        if index_document(rows) != index:
            fail(errors, "Collection revision does not match its indexed editions")
    except (KeyError, TypeError, ValueError) as exc:
        return [*errors, f"Incomplete edition revision metadata: {exc}"]
    errors.extend(inventory_errors(out, rows))
    for work_id in selected:
        if work_id not in indexed:
            fail(errors, f"{work_id}: missing from the publication index")
            continue
        row = indexed[work_id]
        file_errors = artifact_errors(out, row)
        if file_errors:
            errors.extend(file_errors)
            continue
        if row.get("legacy"):
            fail(errors, f"{work_id}: legacy edition requires a rebuild to verify its revision and source attribution")
            continue
        meta, _, _, documented, source_hash = edition_source(root, works[work_id], format_date, css, epub_css)
        try:
            datetime.strptime(row["modified"], "%Y-%m-%dT%H:%M:%SZ")
            if row["modified"] < documented:
                fail(errors, f"{work_id}: package date predates the source revision {documented}")
            if row["source_sha256"] != source_hash:
                fail(errors, f"{work_id}: edition does not match its canonical source inputs")
            version = revision_version(row["release_label"], row["modified"], row["content_sha256"])
            if not re.fullmatch(r"[0-9a-f]{64}", row["content_sha256"]) or row["edition_version"] != version:
                fail(errors, f"{work_id}: edition version differs from the revision record")
            if row["title"] != (meta.get("title_en") or meta.get("title") or work_id) or row["source"] != meta.get("source", {}).get("url", ""):
                fail(errors, f"{work_id}: index title or source is stale")
            print_html = out / row["print"]
            source = print_html.read_text(encoding="utf-8")
            stylesheet = print_html.with_name("publication.css").read_text(encoding="utf-8")
            validate_epub(out / row["epub"], row, meta, source, stylesheet, errors)
            if stylesheet != css:
                fail(errors, f"{work_id}: print stylesheet differs from its source")
        except (KeyError, TypeError, ValueError) as exc:
            fail(errors, f"{work_id}: invalid publication revision: {exc}")
            continue
        if REQUIRED_CAVEAT not in source:
            fail(errors, f"{work_id}: print edition lacks the required editorial caveat")
        if re.search(r"<(?:script|button|iframe)\b", source, re.I):
            fail(errors, f"{work_id}: print edition contains interface chrome or active embeds")
        if "institutional source record" not in source:
            fail(errors, f"{work_id}: print edition lacks institutional provenance")
        page = html.fromstring(source)
        title_credits = page.xpath('//header[contains(@class, "title-page")]/p/text()')
        colophon = page.xpath('string(//section[@id="provenance"]//dt[.="Authorship"]/following-sibling::dd[1])')
        if credit(meta) not in title_credits or colophon != credit(meta):
            fail(errors, f"{work_id}: print title or colophon has incorrect authorship")
        if f"Trithemius Corpus · Reading Edition {version}" not in title_credits:
            fail(errors, f"{work_id}: print revision differs from index")
    for token in ["@page", "break-inside: avoid", "table-layout: fixed", "@media print"]:
        if token not in css:
            fail(errors, f"publication.css lacks print contract {token!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epubcheck", help="EPUBCheck executable or wrapper")
    parser.add_argument("--work", action="append", help="Validate only this work id")
    args = parser.parse_args()
    errors = validate_exports(ROOT, OUT, args.work)
    selected = args.work or list(export_context(ROOT)[0])
    if args.epubcheck and not errors:
        run_epubcheck([OUT / "epub" / f"{work}.epub" for work in selected], args.epubcheck, errors)
    if errors:
        print("Publication export validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Publication export validation passed: {len(selected)} EPUB 3.3 + paged-HTML editions")
    if not args.epubcheck:
        print("  structural validation complete; pass --epubcheck for official EPUBCheck validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
