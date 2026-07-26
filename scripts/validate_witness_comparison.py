#!/usr/bin/env python3
"""Release checks for the witness-comparison pilot."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_witness_comparison import ROOT, SCHEMA, SOURCE, TEI, load_comparison, make_tei  # noqa: E402

from jsonschema import Draft202012Validator  # noqa: E402


def schema_errors() -> list[str]:
    """Validate the committed data and schema itself with jsonschema.

    Mirrors the passage validator: the schema file must be a legal
    Draft 2020-12 schema, and the human-verified data must satisfy it.
    """
    errors: list[str] = []
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # OSError, JSONDecodeError, jsonschema.SchemaError
        errors.append(f"{SCHEMA.name}: {exc}")
        return errors
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        location = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{SOURCE.name}: {location}: {err.message}")
    return errors


def main() -> None:
    problems = schema_errors()
    if problems:
        raise SystemExit("witness comparison schema validation failed:\n  " + "\n  ".join(problems))

    data = load_comparison()
    assert data["summary"]["substantive"] == 0, "no substantive variation may be invented"
    assert data["summary"]["ocr_error"] == len(data["ocr_observations"]), "ocr_error total must match observations"
    out = ROOT / "site" / "dist" / "data" / "witness-comparisons"
    tei_path = out / "anna-tetrastichon.tei.xml"
    assert tei_path.read_bytes() == make_tei(data), "committed TEI is stale or nondeterministic"
    tree = ET.parse(tei_path)
    apps = tree.findall(f".//{{{TEI}}}app")
    assert len(apps) == len(data["variation_units"]), "app count must match variation units"
    assert all(app.find(f"{{{TEI}}}lem") is not None for app in apps), "every app needs a lemma"
    assert all(len(app.findall(f"{{{TEI}}}rdg")) == 3 for app in apps), "every app needs three readings"
    for artifact in ("anna-tetrastichon.json", "anna-tetrastichon.tsv"):
        assert (out / artifact).exists(), f"missing download artifact {artifact}"
    html = (ROOT / "site" / "dist" / "witness-comparison.html").read_text(encoding="utf-8")
    for needle in ("Diplomatic", "Normalized", "OCR is not variation", "Download TEI", "comparison-ribbons", "human-verified"):
        assert needle in html, f"comparison page lacks {needle!r}"
    print(f"witness comparison validation passed: {data['id']}")


if __name__ == "__main__":
    main()
