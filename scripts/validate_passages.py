"""Validate passage indexes, structured annotations, and pilot TEI exports."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path

from lxml import etree
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

sys.path.insert(0, str(Path(__file__).resolve().parent))
import passage_model as pm  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DIST = Path(os.environ.get("TRITHEMIUS_SITE_DIST", ROOT / "site" / "dist")).resolve()
SCHEMAS = ROOT / "data" / "schemas"
RNG_PATH = SCHEMAS / "trithemius-pilot.rng"


@lru_cache(maxsize=1)
def passage_schema_validator() -> Draft202012Validator:
    passage_schema = json.loads(
        (SCHEMAS / "passage-index.schema.json").read_text(encoding="utf-8")
    )
    annotation_schema = json.loads(
        (SCHEMAS / "annotation.schema.json").read_text(encoding="utf-8")
    )
    registry = Registry().with_resource(
        annotation_schema["$id"], Resource.from_contents(annotation_schema)
    )
    return Draft202012Validator(passage_schema, registry=registry)


class IDParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if attr.get("id"):
            self.ids.add(str(attr["id"]))


def source_checks(errors: list[str]) -> None:
    for name in ("annotation.schema.json", "passage-index.schema.json"):
        try:
            schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"data/schemas/{name}: {exc}")
    try:
        etree.RelaxNG(etree.parse(str(RNG_PATH)))
    except (OSError, etree.XMLSyntaxError, etree.RelaxNGParseError) as exc:
        errors.append(f"data/schemas/{RNG_PATH.name}: {exc}")

    required_tokens = {
        ROOT / "scripts" / "build_site.py": [
            "stitch_english_with_passages",
            "write_passage_index",
            "write_tei",
        ],
        ROOT / "site" / "static" / "reader.js": [
            "data-passage-id",
            "passageURL",
            "passage: passage",
        ],
        ROOT / "site" / "templates" / "work.html.j2": [
            "rt-copy-link",
            "Passage and annotation index",
        ],
    }
    for path, tokens in required_tokens.items():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{path.relative_to(ROOT).as_posix()}: {exc}")
            continue
        for token in tokens:
            if token not in text:
                errors.append(f"{path.relative_to(ROOT).as_posix()}: missing {token!r}")


def synthetic_determinism_check(errors: list[str]) -> None:
    marked = (
        '<!--PASSAGE-SEG:7--><h2 id="old-heading">Heading</h2>'
        '<p>Visible <span class="anno anno-unclear">[unclear]</span> text.</p>'
        '<ul><li>Alpha</li><li>Beta</li></ul>'
    )
    first = pm.identify_passages(marked, "prdl-99999_synthetic")
    second = pm.identify_passages(marked, "prdl-99999_synthetic")
    if first != second:
        errors.append("passage_model: synthetic passage output is not deterministic")
        return
    rendered, passages, annotations = first
    expected_ids = ["p-en-0007-0001", "p-en-0007-0002", "p-en-0007-0003"]
    if [item["html_id"] for item in passages] != expected_ids:
        errors.append("passage_model: synthetic passage IDs do not match the v1 contract")
    if "old-heading" not in rendered or "p-en-0007-0001" not in rendered:
        errors.append("passage_model: legacy and stable heading targets were not both retained")
    if len(annotations) != 1 or annotations[0]["html_id"] != "a-en-0007-0002-001":
        errors.append("passage_model: visible editorial marker was not structured deterministically")
    if passages[1]["text"] != "Visible [unclear] text.":
        errors.append("passage_model: inline markup changed passage word boundaries")
    if passages[2]["text"] != "Alpha Beta":
        errors.append("passage_model: list items were flattened without a word boundary")

    index = pm.build_passage_index(
        {
            "id": "prdl-99999_synthetic",
            "title": "Synthetic",
            "title_en": "Synthetic",
            "source": {"provider": "Test", "url": "https://example.test/source"},
        },
        [{"n": 7, "latin": "Lorem", "missing": False, "dup_of": None}],
        passages,
        annotations,
        generated_from="synthetic",
    )
    schema_errors = list(passage_schema_validator().iter_errors(index))
    if schema_errors:
        errors.append(f"passage_model: synthetic JSON failed its schema: {schema_errors[0].message}")
    second_index = pm.build_passage_index(
        {
            "id": "prdl-99999_synthetic",
            "title": "Synthetic",
            "title_en": "Synthetic",
            "source": {"provider": "Test", "url": "https://example.test/source"},
        },
        [{"n": 7, "latin": "Lorem", "missing": False, "dup_of": None}],
        passages,
        annotations,
        generated_from="synthetic",
    )
    if pm.passage_index_bytes(index) != pm.passage_index_bytes(second_index):
        errors.append("passage_model: JSON serialization is not byte-stable")
    try:
        schema = etree.RelaxNG(etree.parse(str(RNG_PATH)))
        document = etree.fromstring(pm.tei_bytes(index))
        if not schema.validate(document):
            errors.append(f"passage_model: synthetic TEI failed the pilot schema: {schema.error_log}")
    except (etree.XMLSyntaxError, etree.RelaxNGParseError) as exc:
        errors.append(f"passage_model: synthetic TEI validation failed: {exc}")


def expected_work_ids() -> set[str]:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    return {work["id"] for work in manifest["works"] if not work.get("skip")}


def recomputed_digest(index: dict) -> str:
    unsigned = dict(index)
    unsigned.pop("content_digest", None)
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def page_ids(work_id: str, cache: dict[str, set[str]], errors: list[str]) -> set[str]:
    if work_id in cache:
        return cache[work_id]
    path = DIST / "works" / f"{work_id}.html"
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        errors.append(f"{path}: {exc}")
        cache[work_id] = set()
        return cache[work_id]
    parser = IDParser()
    parser.feed(source)
    parser.close()
    cache[work_id] = parser.ids
    return parser.ids


def validate_index(path: Path, errors: list[str], id_cache: dict[str, set[str]]) -> dict | None:
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: {exc}")
        return None
    work_id = index.get("work", {}).get("id", "")
    for schema_error in list(passage_schema_validator().iter_errors(index))[:5]:
        location = "/".join(str(part) for part in schema_error.absolute_path)
        errors.append(f"{path}: schema error at {location or '<root>'}: {schema_error.message}")
    if path.stem != work_id:
        errors.append(f"{path}: filename does not match work.id")
    if index.get("schema_version") != pm.SCHEMA_VERSION:
        errors.append(f"{path}: unsupported schema_version")
    if index.get("transform_version") != pm.TRANSFORM_VERSION:
        errors.append(f"{path}: unsupported transform_version")
    if index.get("content_digest") != recomputed_digest(index):
        errors.append(f"{path}: content_digest does not match deterministic content")

    segments = index.get("segments", [])
    passages = index.get("passages", [])
    annotations = index.get("annotations", [])
    segment_ids = {item.get("id") for item in segments}
    passage_ids = [item.get("id") for item in passages]
    html_ids = [item.get("html_id") for item in passages]
    annotation_ids = [item.get("id") for item in annotations]
    annotation_html_ids = [item.get("html_id") for item in annotations]
    for label, values in (
        ("passage IDs", passage_ids),
        ("passage HTML IDs", html_ids),
        ("annotation IDs", annotation_ids),
        ("annotation HTML IDs", annotation_html_ids),
    ):
        if len(values) != len(set(values)):
            errors.append(f"{path}: duplicate {label}")

    ids = page_ids(work_id, id_cache, errors)
    annotation_by_id = {item.get("id"): item for item in annotations}
    for passage in passages:
        if passage.get("segment_id") not in segment_ids:
            errors.append(f"{path}: passage references a missing segment")
        if passage.get("html_id") not in ids:
            errors.append(f"{path}: missing HTML passage target {passage.get('html_id')!r}")
        expected = pm.canonical_passage_id(
            work_id, int(passage.get("segment", 0)), int(passage.get("sequence", 0))
        )
        if passage.get("id") != expected:
            errors.append(f"{path}: passage ID violates the deterministic contract")
        for annotation_id in passage.get("annotations", []):
            if annotation_id not in annotation_by_id:
                errors.append(f"{path}: passage references missing annotation {annotation_id!r}")
    passage_id_set = set(passage_ids)
    for annotation in annotations:
        if annotation.get("target", {}).get("source") not in passage_id_set:
            errors.append(f"{path}: annotation target passage is missing")
        if annotation.get("html_id") not in ids:
            errors.append(f"{path}: annotation HTML target is missing")
    return index


def generated_checks(errors: list[str]) -> tuple[int, int, int]:
    for schema_name in (
        "annotation.schema.json",
        "passage-index.schema.json",
        "trithemius-pilot.rng",
    ):
        source = SCHEMAS / schema_name
        published = DIST / "data" / "schemas" / schema_name
        try:
            if source.read_bytes() != published.read_bytes():
                errors.append(f"{published}: published schema is stale")
        except OSError as exc:
            errors.append(f"{published}: {exc}")
    passage_dir = DIST / "data" / "passages"
    files = sorted(passage_dir.glob("*.json")) if passage_dir.is_dir() else []
    if not files:
        errors.append(f"{passage_dir}: no generated passage indexes")
        return 0, 0, 0
    actual = {path.stem for path in files}
    expected = expected_work_ids()
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            errors.append(f"passage indexes missing {len(missing)} work(s): {', '.join(missing[:3])}")
        if extra:
            errors.append(f"passage indexes contain {len(extra)} unexpected work(s): {', '.join(extra[:3])}")

    id_cache: dict[str, set[str]] = {}
    indexes: dict[str, dict] = {}
    passage_count = 0
    annotation_count = 0
    for path in files:
        index = validate_index(path, errors, id_cache)
        if index:
            work_id = index["work"]["id"]
            indexes[work_id] = index
            passage_count += len(index.get("passages", []))
            annotation_count += len(index.get("annotations", []))

    try:
        schema = etree.RelaxNG(etree.parse(str(RNG_PATH)))
    except (OSError, etree.XMLSyntaxError, etree.RelaxNGParseError) as exc:
        errors.append(f"cannot load pilot TEI schema: {exc}")
        return passage_count, annotation_count, 0
    tei_count = 0
    for work_id in sorted(pm.TEI_PILOT_IDS):
        path = DIST / "tei" / f"{work_id}.xml"
        if work_id not in indexes:
            continue
        try:
            document = etree.parse(str(path))
        except (OSError, etree.XMLSyntaxError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        if not schema.validate(document):
            errors.append(f"{path}: pilot TEI schema validation failed: {schema.error_log}")
        expected_bytes = pm.tei_bytes(indexes[work_id])
        if path.read_bytes() != expected_bytes:
            errors.append(f"{path}: TEI is stale relative to the passage index")
        tei_count += 1
    return passage_count, annotation_count, tei_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="validate schemas and deterministic synthetic generation without site artifacts",
    )
    args = parser.parse_args()
    errors: list[str] = []
    source_checks(errors)
    synthetic_determinism_check(errors)
    counts = (0, 0, 0)
    if not args.source_only:
        counts = generated_checks(errors)
    if errors:
        print("Passage validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Passage validation passed.")
    if args.source_only:
        print("  deterministic synthetic model + JSON/RNG schemas")
    else:
        print(f"  passages: {counts[0]}")
        print(f"  annotations: {counts[1]}")
        print(f"  pilot TEI exports: {counts[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
