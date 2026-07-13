"""Run the Qwen3-VL dual-context corpus refresh.

This orchestrates the existing low-level scripts:

1. `qwen3vl_ocr_batch.py` for page-image OCR into
   translations/_reocr/<engine>/
2. `dual_context_retranslate.py` for GPT-5.5 translation using:
   primary Qwen3-VL OCR, secondary existing OCR, and prior English context.

The default order is smallest works first. The script is resume-friendly because
the underlying OCR and translation scripts skip existing page/chunk outputs
unless force flags are supplied.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"
CACHE = ROOT / ".cache" / "qwen3vl-corpus-pipeline"

DEFAULT_ENGINE = "qwen3vl-4b-instruct-q6"
OUT_BACKEND = "qwen3vl-dual-gpt55"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False) + "\n")


def prdl_number(work_id: str) -> str | None:
    prefix = work_id.split("_", 1)[0]
    if prefix.startswith("prdl-"):
        return prefix.removeprefix("prdl-")
    return None


def skipped_prdl_numbers() -> set[str]:
    manifest = ROOT / "manifest.json"
    if not manifest.exists():
        return set()
    data = json.loads(read_text(manifest))
    skipped: set[str] = set()
    for work in data.get("works", []):
        if not work.get("skip"):
            continue
        source = work.get("source") if isinstance(work.get("source"), dict) else {}
        prdl_id = source.get("prdl_id")
        if prdl_id:
            skipped.add(str(prdl_id))
        work_id = work.get("id")
        if isinstance(work_id, str):
            number = prdl_number(work_id)
            if number:
                skipped.add(number)
    return skipped


def page_num(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def page_files(work_dir: Path) -> list[Path]:
    return sorted((work_dir / "pages").glob("page_*.png"))


def qwen_root(work_id: str, engine: str) -> Path:
    return CORPUS / work_id / "translations" / "_reocr" / engine


def translation_root(work_id: str, out_backend: str = OUT_BACKEND) -> Path:
    return CORPUS / work_id / "translations" / out_backend / "full"


def is_done_ocr_page(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    return not read_text(path).startswith("[ERROR")


def latest_metrics(work_id: str, engine: str) -> dict[int, dict[str, Any]]:
    metrics = qwen_root(work_id, engine) / "qwen3vl_page_metrics.jsonl"
    latest: dict[int, dict[str, Any]] = {}
    if not metrics.exists():
        return latest
    for line in read_text(metrics).splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        page = row.get("page")
        if isinstance(page, int):
            latest[page] = row
    return latest


def planned_works(args: argparse.Namespace) -> list[dict[str, Any]]:
    skipped = skipped_prdl_numbers()
    requested = set(args.work or [])
    rows: list[dict[str, Any]] = []
    for work_dir in sorted(CORPUS.iterdir()):
        if not work_dir.is_dir() or work_dir.name.startswith("_"):
            continue
        pages = page_files(work_dir)
        if not pages:
            continue
        number = prdl_number(work_dir.name)
        is_skipped = bool(number and number in skipped)
        if is_skipped and not args.include_skipped and work_dir.name not in requested:
            continue
        if requested and work_dir.name not in requested:
            continue
        rows.append(
            {
                "work": work_dir.name,
                "pages": len(pages),
                "full_chars": (work_dir / "full.txt").stat().st_size
                if (work_dir / "full.txt").exists()
                else 0,
                "has_existing_ocr": (work_dir / "full.txt").exists(),
                "manifest_skipped": is_skipped,
            }
        )
    rows.sort(key=lambda row: (row["pages"], row["work"]))
    if args.start_after:
        seen = False
        filtered = []
        for row in rows:
            if seen:
                filtered.append(row)
            elif row["work"] == args.start_after:
                seen = True
        rows = filtered
    if args.limit:
        rows = rows[: args.limit]
    return rows


def status_rows(
    works: list[dict[str, Any]],
    engine: str,
    out_backend: str = OUT_BACKEND,
) -> list[dict[str, Any]]:
    out = []
    for row in works:
        work_id = row["work"]
        qroot = qwen_root(work_id, engine)
        pages = page_files(CORPUS / work_id)
        done_pages = 0
        error_pages = []
        for image in pages:
            txt = qroot / f"page_{page_num(image):03d}.txt"
            if is_done_ocr_page(txt):
                done_pages += 1
            elif txt.exists():
                error_pages.append(page_num(image))
        metrics = latest_metrics(work_id, engine)
        capped_pages = sorted(
            page
            for page, metric in metrics.items()
            if metric.get("capped") or metric.get("error")
        )
        trans_dir = translation_root(work_id, out_backend)
        translated_chunks = len(list(trans_dir.glob("full_chunk_*.md"))) if trans_dir.exists() else 0
        out.append(
            {
                **row,
                "engine": engine,
                "qwen_pages_done": done_pages,
                "qwen_pages_total": len(pages),
                "qwen_error_pages": error_pages,
                "qwen_capped_or_error_pages": capped_pages,
                "qwen_full_exists": (qroot / "full.txt").exists(),
                "translated_chunks": translated_chunks,
                "translation_dir": str(trans_dir),
            }
        )
    return out


def print_status(rows: list[dict[str, Any]], engine: str) -> None:
    total_pages = sum(row["qwen_pages_total"] for row in rows)
    done_pages = sum(row["qwen_pages_done"] for row in rows)
    total_chunks = sum(row["translated_chunks"] for row in rows)
    capped_works = sum(1 for row in rows if row["qwen_capped_or_error_pages"])
    print(
        f"engine={engine}\n"
        f"works={len(rows)} qwen_pages={done_pages}/{total_pages} "
        f"translated_chunks={total_chunks} works_with_qwen_warnings={capped_works}"
    )
    print("pages  qwen        warn  chunks  work")
    print("-----  ----------  ----  ------  ----")
    for row in rows:
        warn = len(row["qwen_capped_or_error_pages"])
        print(
            f"{row['pages']:5}  "
            f"{row['qwen_pages_done']:4}/{row['qwen_pages_total']:<5}  "
            f"{warn:4}  "
            f"{row['translated_chunks']:6}  "
            f"{row['work']}"
        )


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def command_line(cmd: list[str]) -> str:
    return subprocess.list2cmdline(cmd)


def run_command(
    cmd: list[str],
    *,
    log_path: Path,
    dry_run: bool,
    event_log: Path,
    label: str,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(
        event_log,
        {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "label": label,
            "command": cmd,
            "log": str(log_path),
            "dry_run": dry_run,
        },
    )
    print(f"\n[{label}] {command_line(cmd)}")
    print(f"[{label}] log={log_path}")
    if dry_run:
        return 0

    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        log.write(f"\n# {dt.datetime.now().isoformat(timespec='seconds')} {label}\n")
        log.write(command_line(cmd) + "\n")
        log.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="")
            log.write(line)
            log.flush()
        rc = proc.wait()
        log.write(f"\n# exit_code={rc}\n")
    append_jsonl(
        event_log,
        {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "label": label,
            "returncode": rc,
            "log": str(log_path),
        },
    )
    return rc


def run_ocr(works: list[dict[str, Any]], args: argparse.Namespace, run_dir: Path, event_log: Path) -> int:
    if not works:
        print("No works selected for OCR.")
        return 0
    cmd = [sys.executable, str(ROOT / "scripts" / "qwen3vl_ocr_batch.py")]
    for row in works:
        cmd.extend(["--work", row["work"]])
    cmd.extend(["--engine", args.engine])
    cmd.extend(
        [
            "--ctx-size",
            str(args.ocr_ctx_size),
            "--max-tokens",
            str(args.ocr_max_tokens),
            "--parallel",
            str(args.ocr_parallel),
            "--image-tokens",
            str(args.ocr_image_tokens),
            "--split-parts",
            str(args.ocr_split_parts),
            "--page-timeout",
            str(args.ocr_page_timeout),
        ]
    )
    if args.ocr_model_dir:
        cmd.extend(["--model-dir", str(args.ocr_model_dir)])
    if args.ocr_model:
        cmd.extend(["--model", str(args.ocr_model)])
    if args.ocr_mmproj:
        cmd.extend(["--mmproj", str(args.ocr_mmproj)])
    if args.ocr_no_mmproj_offload:
        cmd.append("--no-mmproj-offload")
    if args.ocr_prompt_file:
        cmd.extend(["--prompt-file", str(args.ocr_prompt_file)])
    if args.ocr_extract_ocr_section:
        cmd.append("--extract-ocr-section")
    if args.force_ocr:
        cmd.append("--force")
    if args.ocr_port:
        cmd.extend(["--port", str(args.ocr_port)])
    return run_command(
        cmd,
        log_path=run_dir / "ocr.log",
        dry_run=args.dry_run,
        event_log=event_log,
        label="ocr",
    )


def run_translate(
    works: list[dict[str, Any]],
    args: argparse.Namespace,
    run_dir: Path,
    event_log: Path,
) -> int:
    failures: list[tuple[str, int]] = []
    for index, row in enumerate(works, 1):
        work_id = row["work"]
        if not row["has_existing_ocr"]:
            print(f"\n[translate {index}/{len(works)}] skipping {work_id}: no existing full.txt")
            continue
        if not (qwen_root(work_id, args.engine) / "full.txt").exists():
            print(f"\n[translate {index}/{len(works)}] skipping {work_id}: no Qwen full.txt")
            continue

        if not args.skip_clean_existing:
            clean_cmd = [
                sys.executable,
                str(ROOT / "scripts" / "dual_context_retranslate.py"),
                work_id,
                "--clean-existing",
                "--out-backend",
                args.out_backend,
            ]
            rc = run_command(
                clean_cmd,
                log_path=run_dir / f"translate-{index:03d}-{work_id}-clean.log",
                dry_run=args.dry_run,
                event_log=event_log,
                label=f"clean {index}/{len(works)} {work_id}",
            )
            if rc != 0:
                failures.append((work_id, rc))
                continue

        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "dual_context_retranslate.py"),
            work_id,
            "--new-engine",
            args.engine,
            "--out-backend",
            args.out_backend,
            "--workers",
            str(args.translate_workers),
            "--timeout",
            str(args.translate_timeout),
            "--effort",
            args.translate_effort,
        ]
        if args.force_translate:
            cmd.append("--force")
        if args.allow_ocr_warnings:
            cmd.append("--allow-ocr-warnings")
        if not args.no_fallback_secondary:
            cmd.append("--fallback-secondary-on-ocr-warnings")

        rc = run_command(
            cmd,
            log_path=run_dir / f"translate-{index:03d}-{work_id}.log",
            dry_run=args.dry_run,
            event_log=event_log,
            label=f"translate {index}/{len(works)} {work_id}",
        )
        if rc != 0:
            failures.append((work_id, rc))
            if args.stop_on_translate_failure:
                break
    if failures:
        print("\nTranslation failures:")
        for work_id, rc in failures:
            print(f"  rc={rc} {work_id}")
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=["status", "ocr", "translate", "all"],
        default="status",
        help="status only by default; use all to OCR then translate.",
    )
    parser.add_argument("--work", action="append", help="Limit to a specific work id; repeatable.")
    parser.add_argument("--limit", type=int, help="Limit selected works after sorting smallest first.")
    parser.add_argument("--start-after", help="Resume selection after this work id.")
    parser.add_argument("--include-skipped", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--engine", default=DEFAULT_ENGINE)
    parser.add_argument("--out-backend", default=OUT_BACKEND)

    parser.add_argument("--force-ocr", action="store_true")
    parser.add_argument("--ocr-model-dir", type=Path)
    parser.add_argument("--ocr-model", type=Path)
    parser.add_argument("--ocr-mmproj", type=Path)
    parser.add_argument("--ocr-no-mmproj-offload", action="store_true")
    parser.add_argument("--ocr-prompt-file", type=Path)
    parser.add_argument("--ocr-extract-ocr-section", action="store_true")
    parser.add_argument("--ocr-ctx-size", type=int, default=8192)
    parser.add_argument("--ocr-max-tokens", type=int, default=3200)
    parser.add_argument("--ocr-parallel", type=int, default=1)
    parser.add_argument("--ocr-image-tokens", type=int, default=1024)
    parser.add_argument("--ocr-split-parts", type=int, default=1)
    parser.add_argument("--ocr-page-timeout", type=int, default=900)
    parser.add_argument("--ocr-port", type=int)

    parser.add_argument("--force-translate", action="store_true")
    parser.add_argument("--translate-workers", type=int, default=2)
    parser.add_argument("--translate-timeout", type=int, default=1200)
    parser.add_argument(
        "--translate-effort",
        default="high",
        choices=["low", "medium", "high"],
    )
    parser.add_argument("--allow-ocr-warnings", action="store_true")
    parser.add_argument("--no-fallback-secondary", action="store_true")
    parser.add_argument("--skip-clean-existing", action="store_true")
    parser.add_argument("--stop-on-translate-failure", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    works = planned_works(args)
    rows = status_rows(works, args.engine, args.out_backend)

    status_path = CACHE / f"status-{timestamp()}.json"
    write_text(status_path, json.dumps(rows, indent=2, ensure_ascii=False))
    print_status(rows, args.engine)
    print(f"\nWrote status: {status_path}")

    if args.stage == "status":
        return 0

    run_dir = args.run_dir or CACHE / timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    event_log = run_dir / "events.jsonl"
    write_text(
        run_dir / "selected_works.json",
        json.dumps(works, indent=2, ensure_ascii=False),
    )
    print(f"Run dir: {run_dir}")

    if args.stage in {"ocr", "all"}:
        rc = run_ocr(works, args, run_dir, event_log)
        if rc != 0:
            return rc

    if args.stage in {"translate", "all"}:
        refreshed = status_rows(works, args.engine, args.out_backend)
        rc = run_translate(refreshed, args, run_dir, event_log)
        if rc != 0:
            return rc

    final_rows = status_rows(works, args.engine, args.out_backend)
    final_status = run_dir / "final_status.json"
    write_text(final_status, json.dumps(final_rows, indent=2, ensure_ascii=False))
    print(f"\nWrote final status: {final_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
