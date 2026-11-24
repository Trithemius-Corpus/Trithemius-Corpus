"""Replay the recorded editorial history against an assembled edition."""
from __future__ import annotations

import json
from pathlib import Path
from publication_guard import digest


def recorded_ledgers(root: Path, work_id: str, kind: str) -> list[dict]:
    """Read all declared batches in order, rejecting missing or changed inputs."""
    base = root / "data/translation_disagreements" / work_id
    primary, folder = {
        "corrections": ("corrections.json", "revisions"),
        "scans": ("scan-assessments.json", "scan-revisions"),
    }[kind]
    paths = [p for p in [base / primary, *sorted((base / folder).glob("*.json"))] if p.is_file()]
    spec = base / "review.json"
    declared = json.loads(spec.read_text(encoding="utf-8")).get("edition_history", {}).get(kind) if spec.exists() else None
    names = [p.relative_to(base).as_posix() for p in paths]
    if declared is not None and names != [record["path"] for record in declared]:
        raise ValueError(f"{work_id}: incomplete or unexpected {kind} history")
    ledgers = []
    for i, path in enumerate(paths):
        text = path.read_text(encoding="utf-8")
        if declared is not None and digest(text) != declared[i]["sha256"]:
            raise ValueError(f"{work_id}: {kind} ledger changed: {names[i]}")
        ledger = json.loads(text)
        if ledger.get("work_id", work_id) != work_id or ledger.get("human_review") != "none_documented":
            raise ValueError(f"{path}: invalid review attribution or work")
        # Independent collations can finish on the same calendar day. Older
        # records implicitly start at batch 1. A same-day successor records its number.
        previous = ledgers[-1] if ledgers else None
        sequence = ledger.get("sequence", 1)
        expected = previous.get("sequence", 1) + 1 if previous and ledger["date"] == previous["date"] else 1
        if type(sequence) is not int or sequence != expected or (previous and ledger["date"] < previous["date"]):
            raise ValueError(f"{path}: revision history is out of order")
        ledgers.append(ledger)
    return ledgers


def history(root: Path, work_id: str) -> list[dict]:
    return recorded_ledgers(root, work_id, "corrections")


def frozen_text(root: Path, work_id: str, record: dict) -> str:
    source = (root / record["before_path"]).resolve()
    snapshots = (root / "data/translation_disagreements" / work_id / "snapshots").resolve()
    if not source.is_relative_to(snapshots):
        raise ValueError(f"{record['path']}: missing frozen correction source")
    text = source.read_text(encoding="utf-8")
    if digest(text) != record["before_sha256"]:
        raise ValueError(f"{record['path']}: broken correction history")
    return text


def validate_history(root: Path, work_id: str, ledgers: list[dict]) -> None:
    """Replay every frozen input through each batch and compare the final edition."""
    latest = {}
    for batch in ledgers:
        changed = set()
        for edit in batch["changes"]:
            folder = {"earlier": "works", "t4b": "works-t4b"}[edit["track"]]
            work_dir = (root / folder / work_id).resolve()
            if not all((root / p).resolve().is_relative_to(work_dir) for p in edit["files"]):
                raise ValueError("Correction target is outside the edition")
            changed.update(edit["files"])
        changed.update(edit["path"] for edit in batch.get("metadata_edits", []))
        for edit in batch.get("apparatus_edits", []):
            target = (root / edit["path"]).resolve()
            apparatus = (root / "data/publication/apparatus" / f"{work_id}.json").resolve()
            traces = (root / "data/cipher_traces").resolve()
            if target != apparatus and not (
                target.parent == traces and target.suffix == ".json" and
                json.loads(target.read_text(encoding="utf-8")).get("work_id") == work_id
            ):
                raise ValueError("Apparatus correction belongs to a different work")
            changed.add(edit["path"])
        records = batch["files"]
        if changed != {r["path"] for r in records} or len(changed) != len(records):
            raise ValueError("Correction file inventory differs from its declared edits")
        for record in records:
            path = record["path"]
            source = frozen_text(root, work_id, record)
            if path in latest and latest[path] != source:
                raise ValueError(f"{path}: broken correction history")
            latest[path] = replay(source, path, [batch])
    for path, expected in latest.items():
        if (root / path).read_text(encoding="utf-8") != expected:
            raise ValueError(f"Current edition differs from the correction history: {path}")


def replay(text: str, path: str, ledgers: list[dict]) -> str:
    steps = [(ledger, record) for ledger in ledgers for record in ledger["files"] if record["path"] == path]
    if not steps:
        return text
    for previous, following in zip(steps, steps[1:]):
        if previous[1]["after_sha256"] != following[1]["before_sha256"]:
            raise ValueError(f"{path}: disconnected correction history")
    checksum = digest(text)
    if checksum == steps[-1][1]["after_sha256"]:
        return text
    start = next((i for i, (_, r) in enumerate(steps) if r["before_sha256"] == checksum), None)
    if start is None:
        raise ValueError(f"{path}: assembled text differs from the documented correction inputs")
    for ledger, record in steps[start:]:
        changes = [c for c in ledger["changes"] if path in c["files"]]
        changes.extend(c for c in ledger.get("metadata_edits", []) if c["path"] == path)
        changes.extend(c for c in ledger.get("apparatus_edits", []) if c["path"] == path)
        for change in changes:
            occurrences = change.get("occurrences", 1)
            if type(occurrences) is not int or occurrences < 1 or text.count(change["before"]) != occurrences:
                raise ValueError(f"{path}: original wording is missing or ambiguous")
            text = text.replace(change["before"], change["after"], occurrences)
        if digest(text) != record["after_sha256"]:
            raise ValueError(f"{path}: replay does not match the accepted revision")
    return text


def same_numbered_chunks(stage: Path, published: Path) -> bool:
    files = {p.name for p in (stage / "chunks").glob("full_chunk_*.md")}
    existing = {p.name for p in (published / "chunks").glob("full_chunk_*.md")}
    return bool(files) and files == existing and all(
        (stage / "chunks" / name).read_text(encoding="utf-8")
        == (published / "chunks" / name).read_text(encoding="utf-8") for name in files)


def restore_terminal_newlines(text: str, path: str, root: Path, work_id: str, ledgers: list[dict]) -> str:
    """The standard extractor strips final blank lines. Recover only an exact recorded file."""
    records = [r for batch in ledgers for r in batch["files"] if r["path"] == path]
    approved = {r[key] for r in records for key in ("before_sha256", "after_sha256")}
    if digest(text) not in approved:
        for record in records:
            frozen = frozen_text(root, work_id, record)
            candidate = text.rstrip("\n") + frozen[len(frozen.rstrip("\n")):]
            if digest(candidate) in approved:
                return candidate
    return text


def restore_track(root: Path, work_id: str, track: str, stage: Path, published: Path) -> None:
    folder = "works-t4b" if track == "t4b" else "works"
    prefix = f"{folder}/{work_id}/"
    ledgers = history(root, work_id)
    changes = [c for ledger in ledgers for c in ledger["changes"] if c["track"] == track]
    paths = {path for c in changes for path in c["files"]}
    # Apply chunk corrections before verifying the assembled reading text.
    for path in sorted(paths, key=lambda p: (p.endswith("/english.md"), p)):
        if not path.startswith(prefix):
            raise ValueError(f"Unexpected correction target {path}")
        target = (stage / path[len(prefix):]).resolve()
        if not target.is_relative_to(stage.resolve()):
            raise ValueError(f"Invalid correction target {path}")
        text = target.read_text(encoding="utf-8")
        if track == "earlier" and target.parent == (stage / "chunks").resolve():
            text = restore_terminal_newlines(text, path, root, work_id, ledgers)
        if target == (stage / "english.md").resolve():
            master = published / "english.md"
            if master.is_file() and same_numbered_chunks(stage, published):
                # Both tracks include separately edited masters. Preserve those
                # readings only for an exact chunk set and a hash accepted by replay.
                text = master.read_text(encoding="utf-8")
        target.write_text(replay(text, path, ledgers), encoding="utf-8", newline="\n")
    if changes:
        errata = stage / "ERRATA.md"
        if not errata.exists():
            import scan_evidence
            lines = [f"# Editorial corrections — {work_id}"]
            for ledger in ledgers:
                scans = scan_evidence.load(root, work_id, as_of=ledger["date"], sequence=ledger.get("sequence", 1))
                for c in ledger["changes"]:
                    if c["track"] != track:
                        continue
                    assessed = scans[c["item_id"]]
                    lines += [f"\n## {ledger['date']} · {c['item_id']}\n", ledger["review_method"],
                              f"\nPrevious wording: {c['before']}\n\nRevised wording: {c['after']}"]
                    if assessed:
                        lines += [assessed["normalized_latin"], assessed["image"]["image_url"]]
                    for key in c.get("supporting_scans", []):
                        lines += [scans[key]["normalized_latin"], scans[key]["image"]["image_url"]]
                    for anchor in c.get("resolved_annotations", []):
                        lines.append(f'<span id="{anchor}"></span>')
            errata.write_text("\n".join(lines) + "\n", encoding="utf-8")
        errata_text = errata.read_text(encoding="utf-8")
        if any(any(c[key] not in errata_text for key in ("item_id", "before", "after")) for c in changes):
            raise ValueError(f"{work_id}: missing edition errata")
        meta_path = stage / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        prior = published / "metadata.json"
        old = json.loads(prior.read_text(encoding="utf-8")) if prior.exists() else {}
        info = old.get("ai_corrections", {}).copy()
        last_edit = max(batch["date"] for batch in ledgers if any(c["track"] == track for c in batch["changes"]))
        info.update(date=last_edit, count=len(changes), human_review="none_documented")
        info.setdefault("note", "AI scan-supported corrections are recorded in the edition errata. Historical audits predate these edits.")
        meta["ai_corrections"] = info
        if track == "earlier" and "unclear_count" in old:
            meta["unclear_count"] = old["unclear_count"]
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if (published / "ERRATA.md").is_file() and not paths and (published / "english.md").is_file():
        if (stage / "english.md").read_text(encoding="utf-8") != (published / "english.md").read_text(encoding="utf-8"):
            raise ValueError(f"{work_id}: reassembly conflicts with an edition with recorded errata")
