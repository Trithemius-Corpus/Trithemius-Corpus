"""Validate committed EPUB and paged-HTML publication exports."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "dist" / "editions"
EPUB_NS = {"opf": "http://www.idpf.org/2007/opf", "x": "http://www.w3.org/1999/xhtml"}
REQUIRED_CAVEAT = "This is a machine-assisted English reading edition, not a critical edition."


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_epub(path: Path, work_id: str, errors: list[str]) -> None:
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
            text = archive.read("EPUB/introduction.xhtml").decode("utf-8")
            if REQUIRED_CAVEAT not in text:
                fail(errors, f"{work_id}: EPUB lacks the required editorial caveat")
            provenance = archive.read("EPUB/provenance.xhtml").decode("utf-8")
            if "institutional source record" not in provenance or "Methodology and limitations" not in provenance:
                fail(errors, f"{work_id}: EPUB provenance links are incomplete")
            nav = parsed.get("EPUB/nav.xhtml")
            if nav is not None:
                nav_types = {el.attrib.get("{http://www.idpf.org/2007/ops}type") for el in nav.findall(".//x:nav", EPUB_NS)}
                if not {"toc", "landmarks"}.issubset(nav_types):
                    fail(errors, f"{work_id}: navigation lacks toc or landmarks")
            opf_text = archive.read("EPUB/package.opf").decode("utf-8")
            for token in ["schema:accessMode", "schema:accessibilityFeature", "schema:accessibilityHazard", "dc:language"]:
                if token not in opf_text:
                    fail(errors, f"{work_id}: package metadata lacks {token}")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        fail(errors, f"{work_id}: unreadable EPUB: {exc}")


def run_epubcheck(paths: list[Path], command: str, errors: list[str]) -> None:
    for path in paths:
        proc = subprocess.run([command, str(path)], text=True, capture_output=True, check=False)
        if proc.returncode:
            output = (proc.stdout + proc.stderr).strip()
            fail(errors, f"{path.name}: EPUBCheck failed\n{output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epubcheck", help="EPUBCheck executable or wrapper")
    parser.add_argument("--work", action="append", help="Validate only this work id")
    args = parser.parse_args()
    errors: list[str] = []
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    expected = [w["id"] for w in manifest["works"] if not w.get("skip")]
    selected = args.work or expected
    index_path = OUT / "index.json"
    if not index_path.exists():
        fail(errors, "missing editions/index.json")
        index = {"works": []}
    else:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    indexed = {row.get("id") for row in index.get("works", [])}
    if not args.work and indexed != set(expected):
        fail(errors, f"edition index differs from {len(expected)} publishable works")
    epub_paths: list[Path] = []
    for work_id in selected:
        epub = OUT / "epub" / f"{work_id}.epub"
        print_html = OUT / "print" / work_id / "index.html"
        print_css = OUT / "print" / work_id / "publication.css"
        for path in [epub, print_html, print_css]:
            if not path.exists():
                fail(errors, f"{work_id}: missing {path.relative_to(ROOT)}")
        if epub.exists():
            epub_paths.append(epub)
            validate_epub(epub, work_id, errors)
        if print_html.exists():
            source = print_html.read_text(encoding="utf-8", errors="replace")
            if REQUIRED_CAVEAT not in source:
                fail(errors, f"{work_id}: print edition lacks the required editorial caveat")
            if re.search(r"<(?:script|button|iframe)\b", source, re.I):
                fail(errors, f"{work_id}: print edition contains interface chrome or active embeds")
            if "institutional source record" not in source:
                fail(errors, f"{work_id}: print edition lacks institutional provenance")
    css = (ROOT / "site" / "static" / "publication.css").read_text(encoding="utf-8")
    for token in ["@page", "break-inside: avoid", "table-layout: fixed", "@media print"]:
        if token not in css:
            fail(errors, f"publication.css lacks print contract {token!r}")
    if args.epubcheck and epub_paths:
        run_epubcheck(epub_paths, args.epubcheck, errors)
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
