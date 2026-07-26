#!/usr/bin/env python3
"""Validate and publish the human-verified witness-comparison pilot."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "witness_comparisons" / "anna-tetrastichon.json"
SCHEMA = ROOT / "data" / "schemas" / "witness-comparison.schema.json"
OUT = ROOT / "site" / "dist" / "data" / "witness-comparisons"
TEI = "http://www.tei-c.org/ns/1.0"
ET.register_namespace("", TEI)


def load_comparison(path: Path = SOURCE) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    witnesses = data["witnesses"]
    ids = [w["id"] for w in witnesses]
    if not 2 <= len(ids) <= 3 or len(ids) != len(set(ids)):
        raise ValueError("comparison requires two or three distinct witnesses")
    if data["verified"]["status"] != "human-verified-from-facsimile":
        raise ValueError("variant publication requires human facsimile verification")
    for witness in witnesses:
        if len(witness["diplomatic"]) != 4 or len(witness["normalized"]) != 4:
            raise ValueError(f"{witness['id']} must contain four diplomatic and normalized lines")
        for field in ("manifest", "canvas", "image_service", "image"):
            if not witness[field].startswith("https://"):
                raise ValueError(f"{witness['id']} lacks an HTTPS {field}")
    allowed = {"substantive", "orthographic", "punctuation", "unresolved"}
    for unit in data["variation_units"]:
        if unit["type"] not in allowed:
            raise ValueError("OCR observations may not enter the textual apparatus")
        if set(unit["readings"]) != set(ids):
            raise ValueError(f"{unit['id']} must provide one reading per witness")
    if any(item["type"] != "ocr-error" for item in data["ocr_observations"]):
        raise ValueError("raw OCR disagreements must be classified as OCR errors")
    counts = {name: 0 for name in ("substantive", "orthographic", "punctuation", "unresolved")}
    for unit in data["variation_units"]:
        counts[unit["type"]] += 1
    counts["ocr_error"] = len(data["ocr_observations"])
    if counts != data["summary"]:
        raise ValueError(f"summary is not recomputable: {counts!r}")
    data["computed"] = {"witness_ids": ids, "line_count": 4, "counts": counts}
    return data


def make_tei(data: dict) -> bytes:
    q = lambda name: f"{{{TEI}}}{name}"
    root = ET.Element(q("TEI"))
    header = ET.SubElement(root, q("teiHeader"))
    file_desc = ET.SubElement(header, q("fileDesc"))
    title_stmt = ET.SubElement(file_desc, q("titleStmt"))
    ET.SubElement(title_stmt, q("title")).text = data["title"]
    publication = ET.SubElement(file_desc, q("publicationStmt"))
    ET.SubElement(publication, q("p")).text = "Trithemius Corpus; generated deterministically from committed, human-verified data."
    source_desc = ET.SubElement(file_desc, q("sourceDesc"))
    list_wit = ET.SubElement(source_desc, q("listWit"))
    for witness in data["witnesses"]:
        node = ET.SubElement(list_wit, q("witness"), {"{http://www.w3.org/XML/1998/namespace}id": witness["id"]})
        node.text = witness["bibliography"] + " "
        ET.SubElement(node, q("ptr"), {"target": witness["canvas"]})
    text = ET.SubElement(root, q("text"))
    body = ET.SubElement(text, q("body"))
    poem = ET.SubElement(body, q("lg"), {"type": "tetrastich"})
    base = data["witnesses"][0]
    units_by_line: dict[int, list[dict]] = {}
    for unit in data["variation_units"]:
        units_by_line.setdefault(unit["line"], []).append(unit)
    for number, normalized in enumerate(base["normalized"], 1):
        line = ET.SubElement(poem, q("l"), {"n": str(number)})
        ET.SubElement(line, q("seg"), {"type": "normalized"}).text = normalized
        for unit in units_by_line.get(number, []):
            app = ET.SubElement(line, q("app"), {"type": unit["type"], "{http://www.w3.org/XML/1998/namespace}id": unit["id"]})
            ET.SubElement(app, q("lem")).text = unit["lemma"]
            for witness in data["witnesses"]:
                ET.SubElement(app, q("rdg"), {"wit": f"#{witness['id']}"}).text = unit["readings"][witness["id"]]
            ET.SubElement(app, q("note")).text = unit["note"]
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def publish(data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "anna-tetrastichon.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "anna-tetrastichon.tei.xml").write_bytes(make_tei(data))
    with (OUT / "anna-tetrastichon.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["unit", "line", "class", "lemma", "witness", "reading", "facsimile", "note"])
        by_id = {w["id"]: w for w in data["witnesses"]}
        for unit in data["variation_units"]:
            for witness_id in data["computed"]["witness_ids"]:
                writer.writerow([unit["id"], unit["line"], unit["type"], unit["lemma"], witness_id,
                                 unit["readings"][witness_id], by_id[witness_id]["canvas"], unit["note"]])


if __name__ == "__main__":
    comparison = load_comparison()
    publish(comparison)
    print(f"witness comparison valid: {comparison['id']} ({len(comparison['witnesses'])} witnesses)")
