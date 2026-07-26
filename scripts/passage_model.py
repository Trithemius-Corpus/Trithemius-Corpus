"""Deterministic passage identity, annotation records, and pilot TEI export.

The public reading view is generated from Markdown chunks aligned to source
segments. This module assigns stable IDs to addressable English block elements
without pretending that the Latin OCR has paragraph-level alignment: each
English passage points to its containing source segment, and the index records
that alignment precision explicitly.

No timestamp is written to generated artifacts. Given the same work metadata,
source segments, and rendered HTML, JSON and TEI output are byte-stable.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable


SCHEMA_VERSION = "1.0"
TRANSFORM_VERSION = "passage-index-v1"
PASSAGE_MARKER_RE = re.compile(r"<!--PASSAGE-SEG:(\d+)-->")
ANNOTATION_RE = re.compile(
    r'<span(?P<attrs>[^>]*\bclass="[^"]*\banno\b[^"]*"[^>]*)>'
    r"(?P<body>.*?)</span>",
    re.I | re.S,
)
ANNOTATION_KIND_RE = re.compile(r"\banno-([a-z][a-z0-9-]*)\b", re.I)
ADDRESSABLE_TAGS = {
    "p": "paragraph",
    "h2": "heading",
    "h3": "heading",
    "h4": "heading",
    "h5": "heading",
    "h6": "heading",
    "ul": "list",
    "ol": "list",
    "table": "table",
    "blockquote": "quote",
    "pre": "preformatted",
}
TEXT_BREAK_TAGS = set(ADDRESSABLE_TAGS) | {
    "br", "dd", "div", "dt", "figcaption", "li", "section", "td", "th", "tr",
}
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
TEI_NS = "http://www.tei-c.org/ns/1.0"
TEI_PILOT_IDS = {
    "prdl-24362_de-laude-scriptorum-manualium",
    "prdl-24390_polygraphiae-libri-vi",
    "prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam",
}


def canonical_segment_id(work_id: str, segment: int) -> str:
    return f"trc:{work_id}:seg-{segment:04d}"


def canonical_passage_id(work_id: str, segment: int, sequence: int) -> str:
    return f"{canonical_segment_id(work_id, segment)}:p-{sequence:04d}"


def passage_html_id(segment: int, sequence: int) -> str:
    return f"p-en-{segment:04d}-{sequence:04d}"


def annotation_html_id(segment: int, sequence: int, annotation: int) -> str:
    return f"a-en-{segment:04d}-{sequence:04d}-{annotation:03d}"


def strip_passage_markers(rendered_html: str) -> str:
    return PASSAGE_MARKER_RE.sub("", rendered_html)


@dataclass
class BlockSpan:
    tag: str
    attrs: dict[str, str]
    start: int
    start_tag_end: int
    end: int
    depth: int


class _BlockSpanParser(HTMLParser):
    """Locate non-nested addressable blocks without rewriting their HTML."""

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_starts = [0]
        self.line_starts.extend(match.end() for match in re.finditer(r"\n", source))
        self.stack: list[str] = []
        self.active: BlockSpan | None = None
        self.blocks: list[BlockSpan] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        start = self._offset()
        start_text = self.get_starttag_text() or ""
        if tag not in VOID_TAGS:
            self.stack.append(tag)
        if self.active is None and tag in ADDRESSABLE_TAGS:
            self.active = BlockSpan(
                tag=tag,
                attrs=self._attrs(attrs),
                start=start,
                start_tag_end=start + len(start_text),
                end=len(self.source),
                depth=len(self.stack),
            )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # None of the passage-bearing elements are expected to be self-closing.
        return

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        start = self._offset()
        close = self.source.find(">", start)
        end = len(self.source) if close < 0 else close + 1
        if tag in self.stack:
            reverse_index = self.stack[::-1].index(tag)
            del self.stack[len(self.stack) - reverse_index - 1 :]
        if self.active is not None and len(self.stack) < self.active.depth:
            self.active.end = end
            self.blocks.append(self.active)
            self.active = None

    def close(self) -> None:
        super().close()
        if self.active is not None:
            self.blocks.append(self.active)
            self.active = None


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.suppressed = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.suppressed += 1
        elif not self.suppressed and tag in TEXT_BREAK_TAGS:
            self.parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.suppressed and tag in TEXT_BREAK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.suppressed:
            self.suppressed -= 1
        elif not self.suppressed and tag in TEXT_BREAK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.suppressed:
            self.parts.append(data)

    @property
    def text(self) -> str:
        return " ".join("".join(self.parts).split())


def plain_text(fragment: str) -> str:
    parser = _PlainTextParser()
    parser.feed(fragment)
    parser.close()
    return parser.text


def _chapter_for_segment(chapters: dict | None, segment: int) -> str | None:
    if not chapters:
        return None
    current = None
    for entry in sorted(chapters.get("entries", []), key=lambda item: item.get("n", 0)):
        number = entry.get("n")
        if isinstance(number, int) and number <= segment:
            current = f"ch-{number}"
        elif isinstance(number, int) and number > segment:
            break
    return current


def _append_attrs(start_tag: str, attributes: dict[str, str]) -> str:
    ending = "/>" if start_tag.endswith("/>") else ">"
    stem = start_tag[: -len(ending)]
    rendered = "".join(
        f' {key}="{html.escape(value, quote=True)}"'
        for key, value in attributes.items()
    )
    return stem + rendered + ending


def _annotate_block(
    block_html: str,
    *,
    work_id: str,
    segment: int,
    sequence: int,
    kind: str,
    existing_id: str,
) -> tuple[str, dict, list[dict]]:
    html_id = passage_html_id(segment, sequence)
    passage_id = canonical_passage_id(work_id, segment, sequence)
    annotation_records: list[dict] = []
    annotation_number = 0

    def replace_annotation(match: re.Match[str]) -> str:
        nonlocal annotation_number
        annotation_number += 1
        attrs = match.group("attrs")
        body_html = match.group("body")
        kind_match = ANNOTATION_KIND_RE.search(attrs)
        annotation_kind = kind_match.group(1).lower() if kind_match else "editorial"
        ann_html_id = annotation_html_id(segment, sequence, annotation_number)
        ann_id = f"{passage_id}:annotation-{annotation_number:03d}"
        start_tag = _append_attrs(
            "<span" + attrs + ">",
            {"id": ann_html_id, "data-annotation-id": ann_id},
        )
        annotation_records.append({
            "id": ann_id,
            "html_id": ann_html_id,
            "type": "Annotation",
            "motivation": "describing",
            "body": {
                "type": "TextualBody",
                "value": plain_text(body_html),
                "purpose": "tagging",
                "format": "text/plain",
                "language": "en",
                "tag": annotation_kind,
            },
            "target": {
                "source": passage_id,
                "selector": {
                    "type": "FragmentSelector",
                    "conformsTo": "https://www.w3.org/TR/media-frags/",
                    "value": ann_html_id,
                },
            },
        })
        return start_tag + body_html + "</span>"

    rewritten = ANNOTATION_RE.sub(replace_annotation, block_html)
    start_end = rewritten.find(">") + 1
    start_tag = rewritten[:start_end]
    passage_attrs = {
        "data-passage-id": html_id,
        "data-passage-uri": passage_id,
        "data-segment": str(segment),
    }
    prefix = ""
    if existing_id:
        prefix = (
            f'<span class="passage-anchor" id="{html_id}" '
            'aria-hidden="true"></span>'
        )
    else:
        passage_attrs = {"id": html_id, **passage_attrs}
    rewritten = prefix + _append_attrs(start_tag, passage_attrs) + rewritten[start_end:]

    record = {
        "id": passage_id,
        "html_id": html_id,
        "segment_id": canonical_segment_id(work_id, segment),
        "segment": segment,
        "sequence": sequence,
        "chapter_id": None,
        "language": "en",
        "kind": kind,
        "text": plain_text(block_html),
        "alignment_precision": "segment",
        "annotations": [item["id"] for item in annotation_records],
        "targets": {
            "reading": f"works/{work_id}.html#{html_id}",
            "parallel": f"works/{work_id}_parallel.html#seg-{segment}",
        },
    }
    return rewritten, record, annotation_records


def identify_passages(
    marked_html: str, work_id: str, chapters: dict | None = None
) -> tuple[str, list[dict], list[dict]]:
    """Replace segment markers with stable passage IDs and structured notes."""
    parts = PASSAGE_MARKER_RE.split(marked_html)
    if len(parts) == 1:
        return marked_html, [], []

    output = [parts[0]]
    passages: list[dict] = []
    annotations: list[dict] = []
    for index in range(1, len(parts), 2):
        segment = int(parts[index])
        fragment = parts[index + 1]
        parser = _BlockSpanParser(fragment)
        parser.feed(fragment)
        parser.close()
        viable = [
            block for block in parser.blocks
            if plain_text(fragment[block.start:block.end])
        ]
        replacements: list[tuple[int, int, str]] = []
        for sequence, block in enumerate(viable, 1):
            rewritten, record, block_annotations = _annotate_block(
                fragment[block.start:block.end],
                work_id=work_id,
                segment=segment,
                sequence=sequence,
                kind=ADDRESSABLE_TAGS[block.tag],
                existing_id=block.attrs.get("id", ""),
            )
            record["chapter_id"] = _chapter_for_segment(chapters, segment)
            passages.append(record)
            annotations.extend(block_annotations)
            replacements.append((block.start, block.end, rewritten))
        for start, end, rewritten in reversed(replacements):
            fragment = fragment[:start] + rewritten + fragment[end:]
        output.append(fragment)
    return "".join(output), passages, annotations


def _segment_source(
    segment: int,
    source_lookup: Callable[[int], dict] | None,
) -> dict:
    if source_lookup is None:
        return {"pages": [], "mapping_precision": "unavailable"}
    result = source_lookup(segment) or {}
    return {
        "pages": list(result.get("pages", [])),
        "mapping_precision": result.get("mapping_precision", "unavailable"),
    }


def build_passage_index(
    work: dict,
    pairs: list[dict],
    passages: list[dict],
    annotations: list[dict],
    *,
    generated_from: str,
    source_lookup: Callable[[int], dict] | None = None,
) -> dict:
    work_id = work["id"]
    source = work.get("source") or {}
    segments = []
    for pair in pairs:
        number = int(pair["n"])
        segments.append({
            "id": canonical_segment_id(work_id, number),
            "html_id": f"seg-{number}",
            "segment": number,
            "latin": pair.get("latin") or "",
            "english_available": not bool(pair.get("missing")),
            "duplicate_of": pair.get("dup_of"),
            "source": _segment_source(number, source_lookup),
        })
    payload = {
        "$schema": "../schemas/passage-index.schema.json",
        "schema_version": SCHEMA_VERSION,
        "transform_version": TRANSFORM_VERSION,
        "generated_from": generated_from,
        "work": {
            "id": work_id,
            "witness_id": work_id.split("_", 1)[0],
            "title": work.get("title") or work_id,
            "title_en": work.get("title_en") or "",
            "source": {
                "provider": source.get("provider") or "",
                "url": source.get("url") or "",
            },
        },
        "alignment": {
            "unit": "source-segment",
            "precision": "segment",
            "note": (
                "English passages are addressable below the segment level; "
                "Latin correspondence is asserted only for the containing source segment."
            ),
        },
        "segments": segments,
        "passages": passages,
        "annotations": annotations,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["content_digest"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def passage_index_bytes(index: dict) -> bytes:
    return (
        json.dumps(index, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def write_passage_index(path: Path, index: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(passage_index_bytes(index))


def _tei(tag: str) -> str:
    return f"{{{TEI_NS}}}{tag}"


def build_tei(index: dict) -> ET.ElementTree:
    """Build the constrained TEI P5 pilot representation for one work."""
    ET.register_namespace("", TEI_NS)
    work = index["work"]
    root = ET.Element(_tei("TEI"), {XML_ID: "trc-" + work["id"]})
    header = ET.SubElement(root, _tei("teiHeader"))
    file_desc = ET.SubElement(header, _tei("fileDesc"))
    title_stmt = ET.SubElement(file_desc, _tei("titleStmt"))
    ET.SubElement(title_stmt, _tei("title")).text = work["title"]
    ET.SubElement(title_stmt, _tei("author")).text = "Johannes Trithemius"
    publication_stmt = ET.SubElement(file_desc, _tei("publicationStmt"))
    ET.SubElement(publication_stmt, _tei("publisher")).text = "Trithemius Corpus"
    availability = ET.SubElement(publication_stmt, _tei("availability"))
    licence = ET.SubElement(availability, _tei("licence"), {
        "target": "https://creativecommons.org/publicdomain/zero/1.0/"
    })
    licence.text = "Generated text and data are released under CC0."
    source_desc = ET.SubElement(file_desc, _tei("sourceDesc"))
    bibl = ET.SubElement(source_desc, _tei("bibl"))
    bibl.text = work["title"] + ". "
    source = work.get("source") or {}
    if source.get("url"):
        ref = ET.SubElement(bibl, _tei("ref"), {"target": source["url"]})
        ref.text = source.get("provider") or "Source witness"
    else:
        ET.SubElement(bibl, _tei("note")).text = source.get("provider") or "Source witness"
    encoding = ET.SubElement(header, _tei("encodingDesc"))
    project = ET.SubElement(encoding, _tei("projectDesc"))
    ET.SubElement(project, _tei("p")).text = index["alignment"]["note"]

    text = ET.SubElement(root, _tei("text"))
    group = ET.SubElement(text, _tei("group"))
    latin_text = ET.SubElement(group, _tei("text"), {XML_LANG: "la", "type": "source-ocr"})
    latin_body = ET.SubElement(latin_text, _tei("body"))
    latin_div = ET.SubElement(latin_body, _tei("div"), {"type": "source-segments"})
    for segment in index["segments"]:
        ab = ET.SubElement(latin_div, _tei("ab"), {
            XML_ID: f"la-seg-{segment['segment']:04d}",
            "n": str(segment["segment"]),
        })
        ab.text = segment["latin"]

    english_text = ET.SubElement(group, _tei("text"), {XML_LANG: "en", "type": "translation"})
    english_body = ET.SubElement(english_text, _tei("body"))
    by_segment: dict[int, list[dict]] = {}
    for passage in index["passages"]:
        by_segment.setdefault(passage["segment"], []).append(passage)
    for segment in index["segments"]:
        number = segment["segment"]
        div = ET.SubElement(english_body, _tei("div"), {
            "type": "segment",
            "n": str(number),
            "corresp": f"#la-seg-{number:04d}",
        })
        for passage in by_segment.get(number, []):
            tag = "head" if passage["kind"] == "heading" else "p"
            attrs = {
                XML_ID: passage["html_id"],
                "n": str(passage["sequence"]),
                "corresp": f"#la-seg-{number:04d}",
            }
            if passage["kind"] not in {"heading", "paragraph"}:
                attrs["type"] = passage["kind"]
            ET.SubElement(div, _tei(tag), attrs).text = passage["text"]

    stand_off = ET.SubElement(root, _tei("standOff"))
    annotation_list = ET.SubElement(stand_off, _tei("listAnnotation"))
    for annotation in index["annotations"]:
        ann = ET.SubElement(annotation_list, _tei("annotation"), {
            XML_ID: annotation["html_id"],
            "motivation": annotation["motivation"],
        })
        target_html = passage_html_id(
            int(re.search(r"seg-(\d+)", annotation["target"]["source"]).group(1)),
            int(re.search(r":p-(\d+)", annotation["target"]["source"]).group(1)),
        )
        note = ET.SubElement(ann, _tei("note"), {
            "target": f"#{target_html}",
            "type": annotation["body"]["tag"],
        })
        note.text = annotation["body"]["value"]
    return ET.ElementTree(root)


def tei_bytes(index: dict) -> bytes:
    tree = build_tei(index)
    ET.indent(tree, space="  ")
    return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True) + b"\n"


def write_tei(path: Path, index: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tei_bytes(index))
