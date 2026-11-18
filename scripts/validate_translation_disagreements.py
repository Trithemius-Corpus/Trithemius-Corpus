"""Validate queue provenance, generated artifacts, local links, and ordering."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

import jsonschema
from lxml import html

import build_translation_disagreements as b
import context_review


def validate_reference(ref: dict, root: Path = b.ROOT) -> None:
    text = b.read(b.resolve_source(ref["path"], root))
    if b.digest(text) != ref["sha256"]:
        raise ValueError("reference source digest mismatch")
    if not 0 <= ref["start"] < ref["end"] <= len(text):
        raise ValueError("reference offsets out of range")
    if text[ref["start"]:ref["end"]] != ref["quote"]:
        raise ValueError("reference quotation does not match offsets")
    if text.count("\n", 0, ref["start"]) + 1 != ref["start_line"]:
        raise ValueError("reference start line mismatch")
    if text.count("\n", 0, ref["end"] - 1) + 1 != ref["end_line"]:
        raise ValueError("reference end line mismatch")


def validate_queue(queue: dict, root: Path = b.ROOT) -> None:
    schema = json.loads(b.read(root / "data/schemas/translation-disagreement-queue.schema.json"))
    jsonschema.Draft202012Validator(schema).validate(queue)
    payload = {k: v for k, v in queue.items() if k != "content_digest"}
    if b.digest(b.json_text(payload)) != queue["content_digest"]:
        raise ValueError("queue digest mismatch")
    source_texts = {}
    for name, source in queue["sources"].items():
        text = b.read(b.resolve_source(source["path"], root))
        if b.digest(text) != source["sha256"]:
            raise ValueError("source manifest digest mismatch")
        source_texts[name] = text
    for track in ("earlier", "t4b"):
        meta = json.loads(source_texts[track + "_metadata"])
        if meta["id"] != queue["work_id"] or b.witness_from_url(meta["source"]["url"]) != queue["witness_id"]:
            raise ValueError("source witness identity mismatch")
        start, end = queue["comparison_scope"][track]
        text = source_texts[track + "_english"]
        if not 0 <= start < end <= len(text):
            raise ValueError("comparison scope out of bounds")
        if len(audit_tokens(text, start, end)) != queue["coverage"][track + "_tokens"]:
            raise ValueError("scope token count mismatch")
    coverage = queue["coverage"]
    if coverage["matched_tokens"] > min(coverage["earlier_tokens"], coverage["t4b_tokens"]):
        raise ValueError("impossible matched-token count")
    counts = Counter(item["priority"] for item in queue["items"])
    if queue["summary"] != {p: counts[p] for p in b.PRIORITY}:
        raise ValueError("summary cannot be recomputed")
    order = [(b.PRIORITY[i["priority"]], i["rank"], i["id"]) for i in queue["items"]]
    if order != sorted(order) or len({i["id"] for i in queue["items"]}) != len(queue["items"]):
        raise ValueError("queue ordering or IDs are invalid")
    for item in queue["items"]:
        if (item["priority"] == "excluded") != (item["disposition"] == "excluded"):
            raise ValueError("inconsistent exclusion")
        for layer in ("english", "latin"):
            for track, ref in item[layer].items():
                validate_reference(ref, root)
                source = queue["sources"][track + "_" + layer]
                if (ref["path"], ref["sha256"]) != (source["path"], source["sha256"]):
                    raise ValueError("reference disagrees with source manifest")
                if layer == "english":
                    start, end = queue["comparison_scope"][track]
                    if not start <= ref["start"] < ref["end"] <= end:
                        raise ValueError("quotation outside comparison scope")
                if "reader_target" in ref:
                    parts = urlsplit(ref["reader_target"])
                    target = b.resolve_source(parts.path, root)
                    if parts.fragment not in html.fromstring(b.read(target)).xpath("//@id"):
                        raise ValueError("invalid local reader fragment")


def audit_tokens(text: str, start: int, end: int) -> list[tuple[str, int, int]]:
    """Independent implementation of the documented token/marker convention."""
    excluded = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        if re.fullmatch(r"(?:\[segment \d+\]|--- Page \d+ ---)\s*", line):
            excluded.append((cursor, cursor + len(line)))
        cursor += len(line)
    result = []
    for match in re.finditer(r"\w+(?:['’]\w+)?", text[start:end]):
        a, z = start + match.start(), start + match.end()
        if not any(x <= a < y for x, y in excluded):
            result.append((match[0].casefold().replace('’', "'"), a, z))
    return result


def validate_inventory(queue: dict, inventory: dict, root: Path = b.ROOT) -> None:
    for key in ("sources", "comparison_scope", "coverage", "work_id", "offset_convention", "candidate_id_version"):
        if inventory[key] != queue[key]:
            raise ValueError(f"inventory disagrees with queue: {key}")
    rows = inventory["candidates"]
    if len(rows) != queue["coverage"]["lexical_difference_count"] or len({r['id'] for r in rows}) != len(rows):
        raise ValueError("candidate count/identity mismatch")
    residuals = []
    for track in ("earlier", "t4b"):
        source = queue["sources"][track + "_english"]
        text = b.read(b.resolve_source(source["path"], root))
        scope = queue["comparison_scope"][track]
        tokens = audit_tokens(text, *scope)
        changed = set()
        previous_end = scope[0]
        for row in rows:
            span = row[track]
            a, z, ca, cz = (span[k] for k in ('start', 'end', 'context_start', 'context_end'))
            if not scope[0] <= ca <= a <= z <= cz <= scope[1] or a < previous_end:
                raise ValueError("overlapping/out-of-scope candidate span")
            if text[a:z] != row[track + "_text"] or text[ca:cz] != row[track + "_context"]:
                raise ValueError("candidate text/context mismatch")
            for n, (_, x, y) in enumerate(tokens):
                if x < z and y > a:
                    if not a <= x < y <= z or n in changed:
                        raise ValueError("partial/repeated token in candidate")
                    changed.add(n)
            previous_end = z
        residual = [t[0] for n, t in enumerate(tokens) if n not in changed]
        if len(residual) != queue['coverage']['matched_tokens']:
            raise ValueError("token conservation failed")
        residuals.append(residual)
    if residuals[0] != residuals[1]:
        raise ValueError("unaccounted lexical differences")


def validate_html(path: Path) -> None:
    document = html.fromstring(b.read(path))
    ids = document.xpath("//@id")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate HTML IDs")
    if len(document.xpath("//main")) != 1 or len(document.xpath("//h1")) != 1:
        raise ValueError("missing review landmarks")
    target_ids = {path.resolve(): set(ids)}
    for href in document.xpath("//a/@href"):
        parsed = urlsplit(href)
        if parsed.scheme:
            if parsed.scheme not in {"http", "https"}:
                raise ValueError("unexpected link scheme")
            continue  # external catalogue record: no live requests in validation
        target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
        if not target.is_relative_to(b.ROOT) or not target.is_file():
            raise ValueError(f"invalid local link: {href}")
        if parsed.fragment and target.suffix == ".html":
            if target not in target_ids:
                target_ids[target] = set(html.fromstring(b.read(target)).xpath("//@id"))
            targets = target_ids[target]
            if unquote(parsed.fragment) not in targets:
                raise ValueError(f"missing target: {href}")
    for node in document.xpath("//input|//select"):
        if not node.xpath("ancestor::label") and not node.get("aria-label"):
            raise ValueError("unlabeled review control")


def validate_context(queue: dict, inventory: dict, folder: Path, spec: dict) -> None:
    report_path = folder / "context-review.json"
    html_path = folder / "context-review.html"
    if "context_review" not in spec:
        if report_path.exists() or html_path.exists() or queue.get("contextual_review") or inventory.get("contextual_review"):
            raise ValueError("Undeclared contextual report or coverage")
        return
    if not report_path.is_file() or not html_path.is_file():
        raise ValueError("Missing contextual report")
    report = json.loads(b.read(report_path))
    expected_snapshot = context_review.inventory_fingerprint(inventory)
    report_digest = context_review.fingerprint({k: v for k, v in report.items() if k != "report_sha256"})
    binding = {"inventory_sha256": expected_snapshot, "report_sha256": report_digest,
               "candidate_count": len(inventory["candidates"])}
    if (queue.get("contextual_review") != binding or inventory.get("contextual_review") != binding
            or any(report.get(k) != v for k, v in binding.items())
            or expected_snapshot != spec["context_review"]["inventory_sha256"]):
        raise ValueError("Contextual report and candidates belong to different snapshots")
    listed = [{"path": Path(x["path"]).name, "sha256": x["sha256"]} for x in report["ledgers"]]
    if listed != spec["context_review"]["ledgers"]:
        raise ValueError("Report omits or changes a declared contextual ledger")
    records = {r["candidate_id"]: r for r in report["items"]}
    if (len(records) != binding["candidate_count"] or len(report["items"]) != len(records)
            or Counter(r["disposition"] for r in records.values()) != report["dispositions"]):
        raise ValueError("Contextual report coverage differs from its dispositions")
    for candidate in inventory["candidates"]:
        if (candidate["id"] not in records or candidate["status"] != "ai_contextually_reviewed"
                or candidate.get("contextual_review") != records[candidate["id"]]):
            raise ValueError(f"Candidate has missing or stale contextual coverage: {candidate['id']}")
    page = html.fromstring(b.read(html_path))
    main = page.xpath("//main")
    if (len(main) != 1 or main[0].get("data-review-digest") != report_digest
            or main[0].get("data-candidate-snapshot") != expected_snapshot):
        raise ValueError("Contextual HTML belongs to a different review snapshot")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default=b.DEFAULT_WORK)
    args = parser.parse_args()
    # Rebuild in memory to detect stale sources, judgments, or output.
    queue = b.build(args.work, check=True)
    validate_queue(queue)
    folder = b.ROOT / "review/translation-disagreements" / args.work
    inventory = json.loads(b.read(folder / "candidates.json"))
    validate_inventory(queue, inventory)
    spec = json.loads(b.read(b.ROOT / "data/translation_disagreements" / args.work / "review.json"))
    validate_context(queue, inventory, folder, spec)
    if (folder/'post-correction-comparison.json').exists():
        current=json.loads(b.read(folder/'post-correction-comparison.json'))
        validate_inventory(current,current)
    candidate_ids = {c["id"] for c in inventory["candidates"]}
    if len(candidate_ids) != inventory["coverage"]["lexical_difference_count"]:
        raise ValueError("candidate coverage or IDs are inconsistent")
    for item in queue["items"]:
        if not set(item["lexical_candidates"]) <= candidate_ids:
            raise ValueError("review links to missing lexical candidates")
    validate_html(folder / "index.html")
    if (folder/'context-review.html').exists():validate_html(folder/'context-review.html')
    for path in (folder / "sources").glob("*.html"):
        validate_html(path)
    print("Disagreement queue validation passed.")
    print(f"  {len(queue['items'])} triage records; {sum(len(i['english'])+len(i['latin']) for i in queue['items'])} exact quotations")
    print("  source hashes, offsets, line numbers, schema, ordering, deterministic rebuild, local links and fragments")
    print("  Validation establishes artifact integrity, not human philological approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
