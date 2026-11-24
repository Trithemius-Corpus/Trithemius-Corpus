"""Bind contextual reviews to their source snapshot and candidate inventory."""
from __future__ import annotations

from collections import Counter
import html
import json
from pathlib import Path

from publication_guard import digest


DISPOSITIONS = {"covered_existing", "no_material_change_found", "layout_furniture",
                "needs_source_review", "alignment_uncertain"}


def fingerprint(value) -> str:
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def inventory_fingerprint(inventory: dict) -> str:
    """Exclude judgments and include the exact aligned spans, text and source identities."""
    spans = [
        [row[key] for key in ("id", "operation", "earlier", "earlier_text", "t4b", "t4b_text")]
        for row in inventory["candidates"]
    ]
    return fingerprint({
        "work": inventory["work_id"], "version": inventory["candidate_id_version"],
        "scope": inventory["comparison_scope"], "offsets": inventory["offset_convention"],
        "sources": {k: v["sha256"] for k, v in inventory["sources"].items()}, "spans": spans,
    })


def references(value, sources: dict, texts: dict):
    if isinstance(value, list):
        for child in value:
            yield from references(child, sources, texts)
    elif isinstance(value, dict):
        key = value.get("source_key", value.get("source"))
        if isinstance(key, str) and {"quote", "start", "end"} <= value.keys():
            if key not in texts:
                raise ValueError(f"Unknown context source {key}")
            text = texts[key]
            start, end = value["start"], value["end"]
            if not 0 <= start <= end <= len(text) or text[start:end] != value["quote"]:
                raise ValueError(f"Context quotation mismatch in {key} at {start}–{end}")
            if value.get("sha256") != sources[key]["sha256"]:
                raise ValueError(f"Context source hash mismatch in {key}")
            first = value.get("start_line", value.get("line_start"))
            last = value.get("end_line", value.get("line_end"))
            if first != text.count("\n", 0, start) + 1 or last != text.count("\n", 0, max(start, end - 1)) + 1:
                raise ValueError(f"Context line mismatch in {key}")
            yield {"source": key, "path": sources[key]["path"], "start_line": first,
                   "end_line": last, "quote": value["quote"]}
        else:
            for child in value.values():
                yield from references(child, sources, texts)


def assemble(root: Path, work: str, spec: dict, inventory: dict, *, scans=None, corrections=None) -> dict | None:
    base = root / "data/translation_disagreements" / work
    parts = {p.name: p for p in base.glob("context-review-*.json")}
    config = spec.get("context_review")
    if config is None and not parts:
        return None
    if not config or not config.get("ledgers"):
        raise ValueError(f"{work}: contextual ledgers must be declared in review.json")
    declared = [p["path"] for p in config["ledgers"]]
    if len(set(declared)) != len(declared) or set(declared) != parts.keys():
        raise ValueError(f"{work}: missing or unexpected contextual ledger: {sorted(set(declared) ^ parts.keys())}")
    snapshot = inventory_fingerprint(inventory)
    if snapshot != config["inventory_sha256"] or config["candidate_id_version"] != inventory["candidate_id_version"]:
        raise ValueError(f"{work}: contextual ledgers belong to a different candidate snapshot")
    texts = {
        k: (root / v["path"]).read_text(encoding="utf-8") for k, v in spec["sources"].items()
        if k.endswith(("_english", "_latin"))
    }
    if any(digest(text) != spec["sources"][key]["sha256"] for key, text in texts.items()):
        raise ValueError(f"{work}: contextual source snapshot changed")
    scans = scans or {}
    corrections = corrections or {}
    rows, findings, ledgers = [], [], []
    checked = 0
    for declared_part in config["ledgers"]:
        path = parts[declared_part["path"]]
        text = path.read_text(encoding="utf-8")
        if digest(text) != declared_part["sha256"]:
            raise ValueError(f"{path.name}: contextual ledger digest mismatch")
        data = json.loads(text)
        version = data.get("candidate_id_version", data.get("snapshot", {}).get("candidate_id_version"))
        if data["work_id"] != work or version != inventory["candidate_id_version"]:
            raise ValueError(f"{path.name}: wrong work or inventory version")
        if any(data["sources"][k]["sha256"] != v["sha256"] for k, v in spec["sources"].items()):
            raise ValueError(f"{path.name}: contextual source digests differ")
        if any(data.get(k) is True for k in ("human_reviewed", "human_verified", "facsimile_verified")):
            raise ValueError(f"{path.name}: unexpected review attribution")
        grouped = [(cid, g["id"]) for g in data["groups"] for cid in g["candidate_ids"]]
        if Counter(grouped) != Counter((r["candidate_id"], r["group_id"]) for r in data["items"]):
            raise ValueError(f"{path.name}: candidate group assignments disagree")
        if any(r["disposition"] not in DISPOSITIONS or not r["rationale"] for r in data["items"]):
            raise ValueError(f"{path.name}: invalid contextual disposition")
        rows.extend(data["items"])
        checked += sum(1 for _ in references(data, spec["sources"], texts))
        for f in data["findings"]:
            record = {
                "id": f["id"], "priority": f.get("priority", f.get("provisional_priority", "P3")),
                "title": f["title"], "assessment": f.get("assessment", ""),
                "next_action": f.get("next_action", "Inspect the source before correcting."),
                "candidate_ids": f.get("candidate_ids", []),
                "evidence": list(references(f, spec["sources"], texts)),
            }
            if f["id"] in corrections:
                record["historical_next_action"] = record["next_action"]
                record["status"] = "ai_scan_checked_corrected_locally"
                record["next_action"] = "Human editorial review of the dated local correction."
                record["followup"] = {"assessment": scans[f["id"]], "correction": corrections[f["id"]]}
            findings.append(record)
        ledgers.append({"path": path.relative_to(root).as_posix(), "sha256": digest(text),
                        "candidates": len(data["items"]), "groups": len(data["groups"])})
    ids = [r["candidate_id"] for r in rows]
    expected = {c["id"] for c in inventory["candidates"]}
    if len(ids) != len(set(ids)) or set(ids) != expected:
        raise ValueError(f"{work}: contextual coverage is incomplete or duplicated")
    if len({f["id"] for f in findings}) != len(findings) or any(set(f["candidate_ids"]) - expected for f in findings):
        raise ValueError(f"{work}: invalid finding identity or candidate reference")
    findings.sort(key=lambda f: (f["priority"], f["id"]))
    report = {
        "schema_version": "1.1", "work_id": work, "inventory_sha256": snapshot,
        "candidate_id_version": inventory["candidate_id_version"],
        "review_method": "AI contextual comparison of the frozen English editions. Dated follow-ups identify individual passages checked against the print.",
        "candidate_count": len(ids), "dispositions": dict(Counter(r["disposition"] for r in rows)),
        "ledgers": ledgers, "items": rows, "findings": findings, "verified_references": checked,
    }
    report["report_sha256"] = fingerprint(report)
    return report


def render(data: dict) -> str:
    esc = html.escape
    cards = []
    for f in data["findings"]:
        refs = "".join(
            f'<h3>{esc(r["source"])}, lines {r["start_line"]}–{r["end_line"]}</h3><pre>{esc(r["quote"])}</pre>'
            for r in f["evidence"]
        )
        followup = f.get("followup")
        if followup:
            scan = followup["assessment"]
            edits = followup["correction"]
            readings = "".join(f'<li>{esc(e["track"])} · {esc(e["after"])}</li>' for e in edits["changes"])
            step = (f'<h3>Scan review and local correction · {esc(edits["date"])}</h3>'
                    f'<p lang="la">{esc(scan["normalized_latin"])}</p><p>{esc(scan["reason"])}</p>'
                    f'<p>Codex AI assessed the print. Human review is pending.</p><ul>{readings}</ul>'
                    f'<p><a href="evidence/{esc(f["id"])}.png">Exact crop</a> · '
                    f'<a href="{esc(scan["image"]["image_url"])}">Printed folio {esc(scan["image"]["label"])}</a></p>')
        else:
            step = f'<p>{esc(f["next_action"])}</p>'
        cards.append(f'<article id="{esc(f["id"])}"><h2>{esc(f["priority"]+" · "+f["title"])}</h2>'
                     f'<p>{esc(f["assessment"])}</p>{step}<details><summary>Frozen source evidence</summary>'
                     f'{refs}</details></article>')
    dispositions = ", ".join(f'{n} {label.replace("_", " ")}' for label, n in data["dispositions"].items())
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Scribes contextual review</title><style>body{{font:16px/1.65 system-ui;margin:24px;background:#f4f2ed;color:#24303d}}main{{max-width:1050px;margin:auto}}article{{background:white;padding:22px;margin:24px 0;border:1px solid #ddd}}h2{{font-size:1.2rem}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:16px/1.6 Georgia}}a{{color:#255d78}}summary{{cursor:pointer}}</style></head><body>
<main data-review-digest="{data['report_sha256']}" data-candidate-snapshot="{data['inventory_sha256']}">
<a href="index.html">Prioritized queue and scan assessments</a><h1>Contextual review of the Scribes comparison</h1>
<p>Each entry records a judgment about the frozen editions. Dated scan reviews give the current reading where a correction has been made.</p>
<p>The original review covered {data['candidate_count']} candidates ({esc(dispositions)}).</p><p><a href="context-review.json">Complete disposition ledger</a></p>{''.join(cards)}</main></body></html>'''
