"""Benchmark Unlimited-OCR GGUF on selected Trithemius pages.

This is a small targeted harness for the dense-page failure mode observed with
Qwen3-VL on prdl-70283. It uses llama-mtmd-cli directly because the model needs
the DeepSeek-OCR chat template and mmproj.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKING = Path(r"E:\trithemius")
CORPUS = WORKING / "data" / "corpus"
MODEL_DIR = ROOT / ".cache" / "models" / "unlimited-ocr-q6"
MODEL = MODEL_DIR / "Unlimited-OCR-Q6_K.gguf"
MMPROJ = MODEL_DIR / "mmproj-Unlimited-OCR-F16.gguf"
OUT = ROOT / ".cache" / "unlimited-ocr-bench"

TEST_PAGES = [
    ("prdl-70283_de-laudibus-sancctissime-matris-anne-tractat", 3),
    ("prdl-70283_de-laudibus-sancctissime-matris-anne-tractat", 5),
    ("prdl-70283_de-laudibus-sancctissime-matris-anne-tractat", 6),
    ("prdl-24364_de-laudibus-sanctissimae-matris-annae", 9),
    ("prdl-24376_ecloga-de-laude-calvorum-ad-carolum", 6),
]

PROMPTS = {
    "free": "Free OCR.",
    "parse": "document parsing.",
    "markdown": "<|grounding|>Convert the document to markdown.",
}

DET_RE = re.compile(r"<\|det\|>[^<]*<\|/det\|>")
LOG_START_RE = re.compile(r"^(?:load_|llama_|common_|clip_|mtmd_|warmup:|print_info:|main:|WARN:|Usage:)")


def llama_bin() -> str:
    return shutil.which("llama-mtmd-cli") or "llama-mtmd-cli"


def page_image(work_id: str, page: int) -> Path:
    return CORPUS / work_id / "pages" / f"page_{page:03d}.png"


def clean_generated(stdout: str) -> str:
    lines = []
    started = False
    for raw in stdout.splitlines():
        line = raw.rstrip()
        if not started:
            if line.startswith("<|det|>") or (
                line.strip()
                and not LOG_START_RE.match(line)
                and not line.startswith(".")
                and "backend" not in line.lower()
            ):
                started = True
            else:
                continue
        if line.startswith("llama_perf_"):
            break
        if LOG_START_RE.match(line):
            continue
        if line.strip() in {"", ".........................................."}:
            continue
        lines.append(line)
    text = "\n".join(lines).strip()
    return DET_RE.sub("", text).replace("<|ref|>", "").replace("<|/ref|>", "").strip()


def repetition_score(text: str) -> float:
    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    return 1.0 - (len(set(lines)) / len(lines))


def run_one(
    *,
    work_id: str,
    page: int,
    prompt_name: str,
    prompt: str,
    max_tokens: int,
    repeat_penalty: float,
    timeout: int,
) -> dict[str, Any]:
    image = page_image(work_id, page)
    cmd = [
        llama_bin(),
        "-m",
        str(MODEL),
        "--mmproj",
        str(MMPROJ),
        "--image",
        str(image),
        "--chat-template",
        "deepseek-ocr",
        "--temp",
        "0",
        "--repeat-penalty",
        str(repeat_penalty),
        "-n",
        str(max_tokens),
        "-p",
        prompt,
    ]
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    seconds = time.time() - started
    generated = clean_generated(proc.stdout or "")
    combined_logs = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return {
        "work": work_id,
        "page": page,
        "prompt": prompt_name,
        "max_tokens": max_tokens,
        "repeat_penalty": repeat_penalty,
        "seconds": round(seconds, 3),
        "returncode": proc.returncode,
        "chars": len(generated),
        "lines": len([line for line in generated.splitlines() if line.strip()]),
        "repetition_score": round(repetition_score(generated), 3),
        "capped_likely": proc.returncode == 0
        and f" /  {max_tokens - 1} runs" in combined_logs,
        "output": generated,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--repeat-penalty", type=float, default=1.08)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--prompts", nargs="+", default=["free"])
    parser.add_argument("--pages", nargs="*", help="WORK_ID:PAGE pairs")
    args = parser.parse_args()

    if not MODEL.exists():
        raise FileNotFoundError(MODEL)
    if not MMPROJ.exists():
        raise FileNotFoundError(MMPROJ)

    pages = TEST_PAGES
    if args.pages:
        pages = []
        for item in args.pages:
            work_id, page = item.rsplit(":", 1)
            pages.append((work_id, int(page)))

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = OUT / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "runs.jsonl"

    for work_id, page in pages:
        for prompt_name in args.prompts:
            prompt = PROMPTS[prompt_name]
            print(f"{work_id} page {page:03d} prompt={prompt_name}", flush=True)
            row = run_one(
                work_id=work_id,
                page=page,
                prompt_name=prompt_name,
                prompt=prompt,
                max_tokens=args.max_tokens,
                repeat_penalty=args.repeat_penalty,
                timeout=args.timeout,
            )
            out_file = out_dir / f"{work_id}_page_{page:03d}_{prompt_name}.txt"
            out_file.write_text(row.pop("output"), encoding="utf-8")
            row["output_file"] = str(out_file)
            with manifest.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(
                f"  chars={row['chars']} lines={row['lines']} "
                f"rep={row['repetition_score']} seconds={row['seconds']} rc={row['returncode']}",
                flush=True,
            )
    print(f"Wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
