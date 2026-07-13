r"""Build a per-chunk public translation backend from the best graded chunks.

The generated backend lives in the working corpus as:

    E:\trithemius\data\corpus\<work_id>\translations\public\full\

It copies the best existing graded translation for each chunk, optionally
leaving flagged/low-scoring chunks missing so the normal translation harness
can refill only those slots. For copied chunks, it writes grade proxy rows to:

    data/corpus/_quality/public_selection.jsonl

The manifest and calibrated scoreboard can then score the public backend
without duplicating thousands of copied grade rows into llm_grades.jsonl.
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKING = Path(r"E:\trithemius")
CORPUS = WORKING / "data" / "corpus"
GRADES = CORPUS / "_quality" / "llm_grades.jsonl"
PUBLIC_SELECTION = CORPUS / "_quality" / "public_selection.jsonl"
PUBLIC_TARGETS = CORPUS / "_quality" / "public_retranslate_targets.jsonl"
PUBLIC_REPORT = CORPUS / "_quality" / "public_selection_report.md"
MANIFEST = REPO / "manifest.json"

MM_TO_OPUS_FAITH = {1: 1.70, 2: 2.80, 3: 3.50, 4: 4.40, 5: 4.30}
MM_TO_OPUS_FLUENT = {1: 1.5, 2: 2.5, 3: 3.5, 4: 4.5, 5: 5.0}
GRADER_RANK = {"claude-opus-4-7": 3, "minimax-m2.7": 2}
PUBLIC_BACKEND = "public"


def norm_record(record: str) -> str:
    record = (record or "").split("/")[-1]
    return record[:-3] if record.endswith(".md") else record


def record_file(record: str) -> str:
    return f"{norm_record(record)}.md"


def adjusted(row: dict, key: str, table: dict[int, float]) -> float | None:
    value = row.get(key)
    if not isinstance(value, int) or not 1 <= value <= 5:
        return None
    if row.get("model") == "claude-opus-4-7":
        return float(value)
    if row.get("graded_by") == "minimax-m2.7":
        return table.get(value, float(value))
    return float(value)


def source_file(work_id: str, backend: str, record: str) -> Path:
    return CORPUS / work_id / "translations" / backend / "full" / record_file(record)


def public_file(work_id: str, record: str) -> Path:
    return source_file(work_id, PUBLIC_BACKEND, record)


def translation_files(work_id: str) -> dict[str, list[str]]:
    root = CORPUS / work_id / "translations"
    out: dict[str, list[str]] = {}
    if not root.is_dir():
        return out
    for backend_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if backend_dir.name == PUBLIC_BACKEND:
            continue
        full = backend_dir / "full"
        if not full.is_dir():
            continue
        records = sorted(norm_record(p.name) for p in full.glob("full_chunk_*.md"))
        if records:
            out[backend_dir.name] = records
    return out


def load_works() -> dict[str, dict]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {w["id"]: w for w in data["works"] if not w.get("skip")}


def load_grades(work_ids: set[str]) -> dict[tuple[str, str, str], dict]:
    by_key: dict[tuple[str, str, str], dict] = {}
    for row_index, line in enumerate(GRADES.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        work_id = row.get("work_id", "")
        if work_id not in work_ids:
            continue
        backend = row.get("translation_backend", "minimax")
        if backend == PUBLIC_BACKEND:
            continue
        record = norm_record(row.get("record") or row.get("chunk", ""))
        if not record:
            continue
        if not source_file(work_id, backend, record).is_file():
            continue
        adj_faith = adjusted(row, "faithful", MM_TO_OPUS_FAITH)
        if adj_faith is None:
            continue
        adj_fluent = adjusted(row, "fluent", MM_TO_OPUS_FLUENT)
        grader = row.get("model") or row.get("graded_by") or "unknown"
        enriched = {
            **row,
            "_row_index": row_index,
            "work_id": work_id,
            "record": record,
            "translation_backend": backend,
            "grader": grader,
            "adj_faith": adj_faith,
            "adj_fluent": adj_fluent,
            "hallucinated": bool(row.get("hallucinated")),
            "preamble": bool(row.get("preamble")),
            "refusal": bool(row.get("refusal")),
        }
        key = (work_id, backend, record)
        current = by_key.get(key)
        priority = (GRADER_RANK.get(grader, 1), row_index)
        if current is None or priority > (GRADER_RANK.get(current["grader"], 1), current["_row_index"]):
            by_key[key] = enriched
    return by_key


def is_risk(row: dict, min_faith: float) -> bool:
    return (
        bool(row.get("hallucinated"))
        or bool(row.get("preamble"))
        or bool(row.get("refusal"))
        or float(row.get("adj_faith", 0.0)) < min_faith
    )


def best_candidate(candidates: list[dict], min_faith: float) -> dict:
    return max(
        candidates,
        key=lambda row: (
            not is_risk(row, min_faith),
            float(row.get("adj_faith", 0.0)),
            float(row.get("adj_fluent") or 0.0),
            GRADER_RANK.get(row.get("grader"), 1),
            int(row.get("_row_index", -1)),
        ),
    )


def proxy_grade(row: dict, now: str) -> dict:
    out = {
        "work_id": row["work_id"],
        "record": row["record"],
        "translation_backend": PUBLIC_BACKEND,
        "selected_from_backend": row["translation_backend"],
        "selection_proxy": True,
        "faithful": row.get("faithful"),
        "fluent": row.get("fluent"),
        "hallucinated": bool(row.get("hallucinated")),
        "preamble": bool(row.get("preamble")),
        "refusal": bool(row.get("refusal")),
        "notes": row.get("notes", ""),
        "ts": now,
    }
    if row.get("model"):
        out["model"] = row["model"]
    if row.get("graded_by"):
        out["graded_by"] = row["graded_by"]
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-faith", type=float, default=3.0)
    parser.add_argument(
        "--leave-risk-missing",
        action="store_true",
        help="Do not copy flagged or adj_faith < min-faith chunks; leave slots for retranslation.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing public files.")
    args = parser.parse_args()

    works = load_works()
    grades = load_grades(set(works))
    selection_rows: list[dict] = []
    target_rows: list[dict] = []
    counters = Counter()
    per_work: dict[str, Counter] = defaultdict(Counter)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for work_id in sorted(works):
        files_by_backend = translation_files(work_id)
        records = sorted(set().union(*(set(v) for v in files_by_backend.values())) if files_by_backend else set())
        for record in records:
            candidates = [
                grades[(work_id, backend, record)]
                for backend in files_by_backend
                if (work_id, backend, record) in grades
            ]
            public_path = public_file(work_id, record)
            has_public = public_path.is_file() and public_path.stat().st_size > 0

            if not candidates:
                if not has_public:
                    target_rows.append({"work_id": work_id, "record": record, "reason": "no_graded_candidate"})
                    counters["targets"] += 1
                    per_work[work_id]["targets"] += 1
                continue

            chosen = best_candidate(candidates, args.min_faith)
            risky = is_risk(chosen, args.min_faith)
            if risky and args.leave_risk_missing:
                if not has_public:
                    target_rows.append({
                        "work_id": work_id,
                        "record": record,
                        "reason": "risk",
                        "best_backend": chosen["translation_backend"],
                        "adj_faith": round(chosen["adj_faith"], 2),
                        "adj_fluent": round(chosen.get("adj_fluent") or 0.0, 2),
                        "hallucinated": chosen["hallucinated"],
                        "preamble": chosen["preamble"],
                        "refusal": chosen["refusal"],
                        "notes": (chosen.get("notes") or "")[:240],
                    })
                    counters["targets"] += 1
                    per_work[work_id]["targets"] += 1
                continue

            src = source_file(work_id, chosen["translation_backend"], record)
            dst = public_path
            if args.overwrite or not has_public:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                counters["copied"] += 1
                per_work[work_id]["copied"] += 1
            else:
                counters["kept"] += 1
                per_work[work_id]["kept"] += 1
            selection_rows.append(proxy_grade(chosen, now))
            counters["selected"] += 1
            per_work[work_id]["selected"] += 1
            if risky:
                counters["selected_risk"] += 1
                per_work[work_id]["selected_risk"] += 1

    write_jsonl(PUBLIC_SELECTION, selection_rows)
    write_jsonl(PUBLIC_TARGETS, target_rows)

    faith_values = []
    for row in selection_rows:
        adj_faith = adjusted(row, "faithful", MM_TO_OPUS_FAITH)
        if adj_faith is not None:
            faith_values.append(adj_faith)
    mean_faith = statistics.mean(faith_values) if faith_values else 0.0

    lines = [
        "# Public backend selection report",
        "",
        f"Generated: {now}",
        "",
        f"- selected proxy grades: {counters['selected']:,}",
        f"- copied files this run: {counters['copied']:,}",
        f"- existing public files kept: {counters['kept']:,}",
        f"- retranslation targets: {counters['targets']:,}",
        f"- risk chunks copied anyway: {counters['selected_risk']:,}",
        f"- mean selected faithful adj: {mean_faith:.2f}",
        "",
        "## Per-work",
        "",
        "| Work | Selected | Copied | Kept | Targets | Risk-copied |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for work_id, counts in sorted(per_work.items()):
        lines.append(
            f"| `{work_id[:60]}` | {counts['selected']} | {counts['copied']} | "
            f"{counts['kept']} | {counts['targets']} | {counts['selected_risk']} |"
        )
    lines.append("")
    PUBLIC_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {PUBLIC_SELECTION}")
    print(f"wrote {PUBLIC_TARGETS}")
    print(f"wrote {PUBLIC_REPORT}")
    print(
        f"selected={counters['selected']} copied={counters['copied']} "
        f"kept={counters['kept']} targets={counters['targets']} "
        f"risk_copied={counters['selected_risk']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
