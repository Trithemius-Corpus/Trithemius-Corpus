"""Evaluate a Qwen3-VL OCR LoRA candidate against base OCR.

The evaluator consumes the dataset builder's JSONL rows as references, then
compares base and candidate predictions from JSONL files or corpus witness
directories. It reports CER, WER, pairwise better/equal/worse rates, blank-page
false positives, repeated-line loop rates, and the v0 promotion gate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TEXT_FIELDS = ("text", "output_text", "prediction", "ocr", "target", "candidate", "response")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def target_text(row: dict[str, Any]) -> str:
    if isinstance(row.get("target"), str):
        return row["target"]
    for message in row.get("messages", []):
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                part.get("text", "") for part in content if isinstance(part, dict) and part.get("text")
            )
    return ""


def prediction_text(row: dict[str, Any]) -> str:
    for field in TEXT_FIELDS:
        value = row.get(field)
        if isinstance(value, str):
            return value
    return ""


def normalize_text(text: str, *, lowercase: bool) -> str:
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text.lower() if lowercase else text


def alpha_count(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def is_blank_ref(text: str) -> bool:
    normalized = normalize_text(text, lowercase=True)
    return normalized in {"", "[blank page]", "blank page"} or alpha_count(normalized) < 20


def repeated_line_loop(text: str) -> bool:
    lines = [normalize_text(line, lowercase=True) for line in text.splitlines()]
    lines = [line for line in lines if len(line) >= 8 and line not in {"[unclear]", "[blank page]"}]
    if len(lines) < 6:
        return False
    run = 1
    last = None
    for line in lines:
        if line == last:
            run += 1
            if run >= 4:
                return True
        else:
            run = 1
            last = line
    counts = Counter(lines)
    _, count = counts.most_common(1)[0]
    return count >= 6 and count / max(len(lines), 1) >= 0.40


def levenshtein(a: list[str] | str, b: list[str] | str) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (left != right)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def load_references(path: Path, split: str | None, sources: set[str] | None) -> list[dict[str, Any]]:
    rows = read_jsonl(path)
    refs = []
    for row in rows:
        if split and row.get("split") != split:
            continue
        if sources and row.get("source") not in sources:
            continue
        text = target_text(row)
        if not text:
            continue
        copied = dict(row)
        copied["reference"] = text
        refs.append(copied)
    return refs


def load_prediction_jsonl(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    if path.suffix.lower() == ".json":
        data = json.loads(read_text(path))
        rows = data if isinstance(data, list) else data.get("rows", [])
    else:
        rows = read_jsonl(path)
    preds: dict[str, str] = {}
    for row in rows:
        example_id = row.get("id") or row.get("example_id")
        if isinstance(example_id, str):
            preds[example_id] = prediction_text(row)
    return preds


def load_corpus_witness_predictions(
    refs: list[dict[str, Any]],
    *,
    corpus_root: Path,
    witness_dir: str | None,
) -> dict[str, str]:
    if not witness_dir:
        return {}
    preds: dict[str, str] = {}
    rel = Path(witness_dir)
    for row in refs:
        if row.get("source") != "trithemius":
            continue
        work_id = row.get("work_id")
        page = row.get("page")
        example_id = row.get("id")
        if not isinstance(work_id, str) or not isinstance(page, int) or not isinstance(example_id, str):
            continue
        path = corpus_root / work_id / rel / f"page_{page:03d}.txt"
        if path.exists():
            preds[example_id] = read_text(path).strip()
    return preds


def score_one(reference: str, prediction: str, *, lowercase: bool) -> dict[str, Any]:
    ref_norm = normalize_text(reference, lowercase=lowercase)
    pred_norm = normalize_text(prediction, lowercase=lowercase)
    ref_words = ref_norm.split()
    pred_words = pred_norm.split()
    return {
        "char_edits": levenshtein(ref_norm, pred_norm),
        "ref_chars": max(len(ref_norm), 1),
        "word_edits": levenshtein(ref_words, pred_words),
        "ref_words": max(len(ref_words), 1),
        "blank_false_positive": is_blank_ref(reference) and alpha_count(prediction) >= 20,
        "loop": repeated_line_loop(prediction),
    }


def aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    char_edits = sum(item["char_edits"] for item in items)
    ref_chars = sum(item["ref_chars"] for item in items)
    word_edits = sum(item["word_edits"] for item in items)
    ref_words = sum(item["ref_words"] for item in items)
    return {
        "examples": len(items),
        "cer": char_edits / ref_chars if ref_chars else None,
        "wer": word_edits / ref_words if ref_words else None,
        "char_edits": char_edits,
        "ref_chars": ref_chars,
        "word_edits": word_edits,
        "ref_words": ref_words,
        "blank_false_positives": sum(1 for item in items if item["blank_false_positive"]),
        "loops": sum(1 for item in items if item["loop"]),
    }


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    sources = set(args.source) if args.source else None
    refs = load_references(args.references, args.split, sources)
    base_preds = load_prediction_jsonl(args.base_predictions)
    candidate_preds = load_prediction_jsonl(args.candidate_predictions)
    base_preds.update(
        load_corpus_witness_predictions(
            refs,
            corpus_root=args.corpus_root,
            witness_dir=args.base_corpus_witness_dir,
        )
    )
    candidate_preds.update(
        load_corpus_witness_predictions(
            refs,
            corpus_root=args.corpus_root,
            witness_dir=args.candidate_corpus_witness_dir,
        )
    )

    scored: list[dict[str, Any]] = []
    missing = Counter()
    pairwise = Counter()
    for ref in refs:
        example_id = ref.get("id")
        if not isinstance(example_id, str):
            continue
        if example_id not in base_preds:
            missing["base"] += 1
            continue
        if example_id not in candidate_preds:
            missing["candidate"] += 1
            continue
        reference = ref["reference"]
        base = score_one(reference, base_preds[example_id], lowercase=args.lowercase)
        candidate = score_one(reference, candidate_preds[example_id], lowercase=args.lowercase)
        if candidate["char_edits"] < base["char_edits"]:
            pairwise["better"] += 1
            judgement = "better"
        elif candidate["char_edits"] > base["char_edits"]:
            pairwise["worse"] += 1
            judgement = "worse"
        else:
            pairwise["equal"] += 1
            judgement = "equal"
        scored.append(
            {
                "id": example_id,
                "source": ref.get("source"),
                "split": ref.get("split"),
                "work_id": ref.get("work_id"),
                "page": ref.get("page"),
                "base": base,
                "candidate": candidate,
                "pairwise": judgement,
            }
        )

    groups: dict[str, dict[str, Any]] = {}
    for name, selector in {
        "all": lambda item: True,
        "trithemius": lambda item: item.get("source") == "trithemius",
        "gt4histocr": lambda item: item.get("source") == "gt4histocr",
    }.items():
        subset = [item for item in scored if selector(item)]
        if not subset:
            continue
        groups[name] = {
            "base": aggregate([item["base"] for item in subset]),
            "candidate": aggregate([item["candidate"] for item in subset]),
        }

    for source in sorted({str(item.get("source")) for item in scored}):
        for split in sorted({str(item.get("split")) for item in scored if item.get("source") == source}):
            subset = [item for item in scored if item.get("source") == source and item.get("split") == split]
            groups[f"{source}:{split}"] = {
                "base": aggregate([item["base"] for item in subset]),
                "candidate": aggregate([item["candidate"] for item in subset]),
            }

    total_pairs = sum(pairwise.values())
    better_equal = (pairwise["better"] + pairwise["equal"]) / total_pairs if total_pairs else 0.0
    worse_rate = pairwise["worse"] / total_pairs if total_pairs else 1.0

    external = groups.get("gt4histocr")
    trithemius = groups.get("trithemius")
    all_group = groups.get("all")

    def rel_improvement(group: dict[str, Any] | None) -> float | None:
        if not group or not group["base"]["cer"]:
            return None
        return (group["base"]["cer"] - group["candidate"]["cer"]) / group["base"]["cer"]

    external_improvement = rel_improvement(external)
    all_improvement = rel_improvement(all_group)
    blank_ok = True
    loop_ok = True
    if all_group:
        blank_ok = all_group["candidate"]["blank_false_positives"] <= all_group["base"]["blank_false_positives"]
        loop_ok = all_group["candidate"]["loops"] <= all_group["base"]["loops"]

    external_signal = None
    if external:
        external_signal = bool(
            external_improvement is not None
            and (
                external_improvement >= args.min_external_cer_improvement
                or (
                    external["candidate"]["cer"] <= external["base"]["cer"]
                    and pairwise["better"] > pairwise["worse"]
                )
            )
        )

    trithemius_pairwise_ok = better_equal >= args.min_better_equal_rate and worse_rate <= args.max_worse_rate
    promotion_pass = bool(
        scored
        and (external_signal if external_signal is not None else trithemius_pairwise_ok)
        and trithemius_pairwise_ok
        and blank_ok
        and loop_ok
        and args.downstream_pass
    )

    return {
        "references": str(args.references),
        "scored_examples": len(scored),
        "missing_predictions": dict(missing),
        "pairwise": {
            "better": pairwise["better"],
            "equal": pairwise["equal"],
            "worse": pairwise["worse"],
            "better_equal_rate": better_equal,
            "worse_rate": worse_rate,
        },
        "groups": groups,
        "relative_cer_improvement": {
            "all": all_improvement,
            "gt4histocr": external_improvement,
            "trithemius": rel_improvement(trithemius),
        },
        "gate": {
            "promotion_pass": promotion_pass,
            "external_signal_pass": external_signal,
            "trithemius_pairwise_pass": trithemius_pairwise_ok,
            "blank_false_positive_pass": blank_ok,
            "loop_rate_pass": loop_ok,
            "downstream_translation_pass": args.downstream_pass,
            "thresholds": {
                "min_external_cer_improvement": args.min_external_cer_improvement,
                "min_better_equal_rate": args.min_better_equal_rate,
                "max_worse_rate": args.max_worse_rate,
            },
        },
        "scored": scored if args.include_rows else [],
    }


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Qwen3-VL OCR LoRA Evaluation",
        "",
        f"- Scored examples: {report['scored_examples']}",
        f"- Missing predictions: {report['missing_predictions']}",
        f"- Promotion pass: {report['gate']['promotion_pass']}",
        "",
        "## Pairwise",
        "",
        "| better | equal | worse | better/equal | worse rate |",
        "| ---: | ---: | ---: | ---: | ---: |",
        (
            f"| {report['pairwise']['better']} | {report['pairwise']['equal']} | "
            f"{report['pairwise']['worse']} | {pct(report['pairwise']['better_equal_rate'])} | "
            f"{pct(report['pairwise']['worse_rate'])} |"
        ),
        "",
        "## OCR Metrics",
        "",
        "| group | base CER | candidate CER | rel CER improvement | base WER | candidate WER | blank FP base/cand | loops base/cand |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group, values in report["groups"].items():
        base = values["base"]
        candidate = values["candidate"]
        improvement = None
        if base["cer"]:
            improvement = (base["cer"] - candidate["cer"]) / base["cer"]
        lines.append(
            f"| {group} | {pct(base['cer'])} | {pct(candidate['cer'])} | {pct(improvement)} | "
            f"{pct(base['wer'])} | {pct(candidate['wer'])} | "
            f"{base['blank_false_positives']}/{candidate['blank_false_positives']} | "
            f"{base['loops']}/{candidate['loops']} |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            f"- External signal pass: {report['gate']['external_signal_pass']}",
            f"- Trithemius pairwise pass: {report['gate']['trithemius_pairwise_pass']}",
            f"- Blank false-positive pass: {report['gate']['blank_false_positive_pass']}",
            f"- Loop-rate pass: {report['gate']['loop_rate_pass']}",
            f"- Downstream translation pass: {report['gate']['downstream_translation_pass']}",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, required=True, help="Dataset JSONL, usually test.jsonl.")
    parser.add_argument("--base-predictions", type=Path)
    parser.add_argument("--candidate-predictions", type=Path)
    parser.add_argument("--corpus-root", type=Path, default=Path("E:/trithemius/data/corpus"))
    parser.add_argument("--base-corpus-witness-dir")
    parser.add_argument("--candidate-corpus-witness-dir")
    parser.add_argument("--split")
    parser.add_argument("--source", action="append")
    parser.add_argument("--lowercase", action="store_true")
    parser.add_argument("--downstream-pass", action="store_true")
    parser.add_argument("--min-external-cer-improvement", type=float, default=0.05)
    parser.add_argument("--min-better-equal-rate", type=float, default=0.70)
    parser.add_argument("--max-worse-rate", type=float, default=0.10)
    parser.add_argument("--include-rows", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("qwen3vl_ocr_lora_eval.json"))
    parser.add_argument("--markdown-out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = evaluate(args)
    write_json(args.out, report)
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("scored_examples", "pairwise", "gate")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
