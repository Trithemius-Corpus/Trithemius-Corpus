"""Benchmark dual vision-OCR passes against existing Trithemius page OCR.

This is a deliberately small harness for targeted OCR experiments. It runs two
Qwen-VL GGUF variants through llama-mtmd-cli, compares their page transcriptions
with the current working-corpus OCR, and writes machine-readable JSON plus a
human-readable Markdown report.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # noqa: BLE001
    Image = None

try:
    import winpty
except Exception:  # noqa: BLE001
    winpty = None


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
DEFAULT_OUT = ROOT / ".cache" / "ocr-bench"

PROMPT = """Transcribe this printed early-modern Latin page exactly.

Rules:
- Output only the transcription.
- Do not translate, summarize, or describe the image.
- Preserve line breaks where practical.
- Preserve visible headings, page numbers, marginal words, tables, and cipher text.
- Expand nothing silently; keep abbreviations and early-modern spellings.
- Use [unclear] only for spans you cannot read.
- If the page is blank, output [blank page].
"""

DEFAULT_MODELS = {
    "instruct": {
        "repo": "unsloth/Qwen3-VL-4B-Instruct-GGUF",
        "model": ROOT / ".cache" / "models" / "qwen3-vl-4b-instruct-q6"
        / "Qwen3-VL-4B-Instruct-Q6_K.gguf",
        "mmproj": ROOT / ".cache" / "models" / "qwen3-vl-4b-instruct-q6"
        / "mmproj-F16.gguf",
    },
    "thinking": {
        "repo": "unsloth/Qwen3-VL-4B-Thinking-GGUF",
        "model": ROOT / ".cache" / "models" / "qwen3-vl-4b-thinking-q6"
        / "Qwen3-VL-4B-Thinking-Q6_K.gguf",
        "mmproj": ROOT / ".cache" / "models" / "qwen3-vl-4b-thinking-q6"
        / "mmproj-F16.gguf",
    },
}

DEFAULT_SAMPLES = [
    {
        "id": "operatione_wrong_source_page_009",
        "work": "prdl-24368_de-operatione-divini-amoris",
        "page": 9,
        "kind": "known wrong-source / botanical hallucination target",
    },
    {
        "id": "operatione_prose_page_010",
        "work": "prdl-24368_de-operatione-divini-amoris",
        "page": 10,
        "kind": "dense devotional prose with abbreviations",
    },
    {
        "id": "clavis_high_modus_page_237",
        "work": "prdl-70281_clavis-generalis-triplex-in-libros-steganographicos",
        "page": 237,
        "kind": "high-modus cipher / small Fraktur strings",
    },
    {
        "id": "clavis_modus_page_251",
        "work": "prdl-70281_clavis-generalis-triplex-in-libros-steganographicos",
        "page": 251,
        "kind": "worked cipher example with Latin cover text",
    },
]


@dataclass(frozen=True)
class Sample:
    id: str
    work: str
    page: int
    kind: str
    image: Path
    baseline: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_page_text(full_text: str, page: int) -> str:
    marker = re.compile(r"^---\s*Page\s+(\d+)\s*---\s*$", re.MULTILINE)
    matches = list(marker.finditer(full_text))
    for i, match in enumerate(matches):
        if int(match.group(1)) != page:
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        return full_text[start:end].strip()
    return ""


def normalize_for_distance(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("ſ", "s").replace("ꝛ", "r")
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (ca != cb)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def token_list(text: str) -> list[str]:
    return re.findall(r"[\wꝛſ]+", normalize_for_distance(text))


def error_rate(candidate: str, reference: str, unit: str) -> float | None:
    cand = normalize_for_distance(candidate)
    ref = normalize_for_distance(reference)
    if not ref:
        return None
    if unit == "word":
        c_tokens = token_list(cand)
        r_tokens = token_list(ref)
        if not r_tokens:
            return None
        return levenshtein(" ".join(c_tokens), " ".join(r_tokens)) / max(1, len(" ".join(r_tokens)))
    return levenshtein(cand, ref) / max(1, len(ref))


def sequence_ratio(candidate: str, reference: str) -> float | None:
    cand = normalize_for_distance(candidate)
    ref = normalize_for_distance(reference)
    if not cand and not ref:
        return 1.0
    if not cand or not ref:
        return 0.0
    return difflib.SequenceMatcher(None, cand, ref, autojunk=False).ratio()


LATIN_HINTS = {
    "et", "in", "de", "cum", "non", "est", "qui", "quod", "ad", "per",
    "ut", "sed", "quia", "sicut", "autem", "igitur", "dei", "domini",
    "anima", "amor", "omnia", "hoc", "illa", "ipsum", "eius", "sanct",
    "modus", "alphabetum", "literae", "significativae", "creator",
}

META_PATTERNS = [
    "provided image",
    "appears to be",
    "no textual content",
    "transcribed text",
    "i cannot",
    "i can't",
    "the page shows",
    "image shows",
    "not part of the text",
]


def text_metrics(text: str, baseline: str) -> dict[str, Any]:
    normalized = normalize_for_distance(text)
    base_norm = normalize_for_distance(baseline)
    lines = [line for line in text.splitlines() if line.strip()]
    words = token_list(text)
    base_lines = [line for line in baseline.splitlines() if line.strip()]
    repeated_lines = len(lines) - len(set(lines))
    latin_hits = sum(1 for word in words if word in LATIN_HINTS)
    bracket_count = text.count("[") + text.count("]")
    meta_hits = [p for p in META_PATTERNS if p in normalized]
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    replacement = text.count("\ufffd")
    think_open = text.count("<think>")
    think_close = text.count("</think>")
    return {
        "chars": len(text),
        "normalized_chars": len(normalized),
        "lines": len(lines),
        "words": len(words),
        "length_ratio_vs_baseline": (
            round(len(normalized) / len(base_norm), 4) if base_norm else None
        ),
        "line_ratio_vs_baseline": (
            round(len(lines) / len(base_lines), 4) if base_lines else None
        ),
        "sequence_ratio_vs_baseline": rounded(sequence_ratio(text, baseline)),
        "cer_vs_baseline": rounded(error_rate(text, baseline, "char")),
        "wer_proxy_vs_baseline": rounded(error_rate(text, baseline, "word")),
        "latin_hint_rate": round(latin_hits / max(1, len(words)), 4),
        "unclear_count": len(re.findall(r"\[unclear\]|\?", text, re.I)),
        "bracket_count": bracket_count,
        "meta_hits": meta_hits,
        "repeated_line_count": repeated_lines,
        "repeated_line_rate": round(repeated_lines / max(1, len(lines)), 4),
        "non_ascii_rate": round(non_ascii / max(1, len(text)), 4),
        "replacement_char_count": replacement,
        "think_open_count": think_open,
        "think_close_count": think_close,
        "unclosed_think": think_open > think_close,
    }


def rounded(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def image_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"path": str(path), "bytes": path.stat().st_size}
    if Image is None:
        return info
    try:
        with Image.open(path) as img:
            info.update({"width": img.width, "height": img.height, "mode": img.mode})
    except Exception as exc:  # noqa: BLE001
        info["image_error"] = str(exc)
    return info


def load_samples(working: Path, sample_defs: list[dict[str, Any]]) -> list[Sample]:
    out: list[Sample] = []
    for item in sample_defs:
        work = item["work"]
        page = int(item["page"])
        full = working / "data" / "corpus" / work / "full.txt"
        image = working / "data" / "corpus" / work / "pages" / f"page_{page:03d}.png"
        if not full.exists():
            raise FileNotFoundError(f"Missing full.txt for {work}: {full}")
        if not image.exists():
            raise FileNotFoundError(f"Missing page image for {work} page {page}: {image}")
        out.append(
            Sample(
                id=item["id"],
                work=work,
                page=page,
                kind=item.get("kind", ""),
                image=image,
                baseline=extract_page_text(read_text(full), page),
            )
        )
    return out


class MemoryPoller:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.peak_working_set = None
        self.peak_private_usage = None
        self._handle = None
        self._is_windows = os.name == "nt"
        if self._is_windows:
            self._open_windows_handle()

    def _open_windows_handle(self) -> None:
        process_query_information = 0x0400
        process_vm_read = 0x0010
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(
            process_query_information | process_vm_read, False, self.pid
        )
        if handle:
            self._handle = handle

    def poll(self) -> None:
        if not self._is_windows or not self._handle:
            return
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        ok = psapi.GetProcessMemoryInfo(
            self._handle, ctypes.byref(counters), ctypes.sizeof(counters)
        )
        if not ok:
            return
        self.peak_working_set = max(
            self.peak_working_set or 0, int(counters.PeakWorkingSetSize)
        )
        self.peak_private_usage = max(
            self.peak_private_usage or 0, int(counters.PrivateUsage)
        )

    def close(self) -> None:
        if self._is_windows and self._handle:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle(self._handle)
            self._handle = None

    def metrics(self) -> dict[str, Any]:
        return {
            "peak_working_set_mb": bytes_to_mb(self.peak_working_set),
            "peak_private_usage_mb": bytes_to_mb(self.peak_private_usage),
        }


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def bytes_to_mb(value: int | None) -> float | None:
    return round(value / (1024 * 1024), 2) if value is not None else None


PERF_RE = re.compile(
    r"(?P<name>load|prompt eval|eval|total) time\s*=\s*"
    r"(?P<ms>[\d.]+)\s*ms(?:\s*/\s*(?P<tokens>\d+)\s*(?:tokens?|runs)"
    r"\s*\([^,]+,\s*(?P<tps>[\d.]+)\s*tokens per second\))?",
    re.I,
)
ANSI_RE = re.compile(
    r"\x1b\][^\x07]*(?:\x07|\x1b\\)|"
    r"\x1b\[[0-?]*[ -/]*[@-~]|"
    r"\x1b[@-Z\\-_]"
)


def parse_perf(log: str) -> dict[str, Any]:
    log = strip_ansi(log)
    out: dict[str, Any] = {}
    for match in PERF_RE.finditer(log):
        key = match.group("name").lower().replace(" ", "_")
        out[f"{key}_ms"] = float(match.group("ms"))
        if match.group("tokens"):
            out[f"{key}_tokens"] = int(match.group("tokens"))
        if match.group("tps"):
            out[f"{key}_tokens_per_second"] = float(match.group("tps"))
    return out


def strip_ansi(text: str) -> str:
    text = ANSI_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text


def repair_mojibake(text: str) -> str:
    markers = ("Ã", "Å", "â", "ê", "ð")
    if not any(marker in text for marker in markers):
        return text
    try:
        repaired = text.encode("cp1252").decode("utf-8")
    except UnicodeError:
        return text
    old_score = sum(text.count(marker) for marker in markers)
    new_score = sum(repaired.count(marker) for marker in markers)
    return repaired if new_score < old_score else text


def strip_llama_logs(output: str) -> str:
    output = strip_ansi(output).replace("\r\n", "\n").replace("\r", "\n")
    image_marker = "image decoded"
    perf_marker = "llama_perf_context_print:"
    image_pos = output.rfind(image_marker)
    if image_pos >= 0:
        start = output.find("\n", image_pos)
        if start >= 0:
            end = output.find(perf_marker, start)
            text = output[start:end if end >= 0 else len(output)]
            return repair_mojibake(text.strip())

    lines = output.splitlines()
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            kept.append(line)
            continue
        if re.match(r"^(load_|llama_|ggml_|mtmd_|common_|sampling:|print_info:)", stripped):
            continue
        if " time =" in stripped and "tokens per second" in stripped:
            continue
        if stripped.startswith("system_info:") or stripped.startswith("generate:"):
            continue
        kept.append(line)
    text = "\n".join(kept).strip()
    text = re.sub(r"^assistant\s*[:：]\s*", "", text, flags=re.I).strip()
    return repair_mojibake(text)


def build_command(
    runner: str,
    model_path: Path,
    mmproj_path: Path,
    sample: Sample,
    prompt_path: Path,
    args: argparse.Namespace,
) -> list[str]:
    return [
        runner,
        "--model",
        str(model_path),
        "--mmproj",
        str(mmproj_path),
        "--image",
        str(sample.image),
        "--file",
        str(prompt_path),
        "--ctx-size",
        str(args.ctx_size),
        "--predict",
        str(args.predict),
        "--threads",
        str(args.threads),
        "--threads-batch",
        str(args.threads_batch),
        "--cache-type-k",
        args.cache_type_k,
        "--cache-type-v",
        args.cache_type_v,
        "--image-max-tokens",
        str(args.image_max_tokens),
        "--image-min-tokens",
        str(args.image_min_tokens),
        "--temp",
        str(args.temperature),
        "--seed",
        str(args.seed),
        "--gpu-layers",
        args.gpu_layers,
        "--no-warmup",
        "--perf",
        "--log-colors",
        "off",
        "--log-verbosity",
        str(args.log_verbosity),
    ]


def run_one(
    label: str,
    model_spec: dict[str, Any],
    sample: Sample,
    out_dir: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    model_path = Path(model_spec["model"])
    mmproj_path = Path(model_spec["mmproj"])
    runner = shutil.which(args.runner) or args.runner
    prompt_path = out_dir / "ocr_prompt.txt"
    prompt_path.write_text(PROMPT, encoding="utf-8")
    command = build_command(runner, model_path, mmproj_path, sample, prompt_path, args)
    if args.use_pty and os.name == "nt" and winpty is not None:
        return run_one_pty(label, model_path, mmproj_path, sample, out_dir, args, command)
    started = time.perf_counter()
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    poller = MemoryPoller(proc.pid)
    timed_out = False
    try:
        while proc.poll() is None:
            poller.poll()
            if time.perf_counter() - started > args.timeout:
                timed_out = True
                proc.kill()
                break
            time.sleep(0.25)
        stdout, stderr = proc.communicate(timeout=5)
    finally:
        poller.poll()
        poller.close()
    wall = time.perf_counter() - started
    combined = f"{stdout}\n{stderr}"
    text = strip_llama_logs(stdout)
    text_path = out_dir / f"{sample.id}.{label}.txt"
    text_path.write_text(text + "\n", encoding="utf-8")
    raw_path = out_dir / f"{sample.id}.{label}.raw.log"
    raw_path.write_text(combined, encoding="utf-8", errors="replace")
    return {
        "sample_id": sample.id,
        "model_label": label,
        "model_path": str(model_path),
        "mmproj_path": str(mmproj_path),
        "command": command,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "wall_seconds": round(wall, 3),
        "stdout_bytes": len(stdout.encode("utf-8", errors="replace")),
        "stderr_bytes": len(stderr.encode("utf-8", errors="replace")),
        "text_path": str(text_path),
        "raw_log_path": str(raw_path),
        "output": text,
        "perf": parse_perf(combined),
        "memory": poller.metrics(),
        "metrics": text_metrics(text, sample.baseline),
    }


def run_one_pty(
    label: str,
    model_path: Path,
    mmproj_path: Path,
    sample: Sample,
    out_dir: Path,
    args: argparse.Namespace,
    command: list[str],
) -> dict[str, Any]:
    started = time.perf_counter()
    cmdline = subprocess.list2cmdline(command[1:])
    pty = winpty.PTY(cols=160, rows=60)
    pty.spawn(command[0], cmdline=cmdline, cwd=str(ROOT))
    poller = MemoryPoller(pty.pid)
    chunks: list[str] = []
    timed_out = False
    while pty.isalive():
        poller.poll()
        try:
            chunk = pty.read(8000, blocking=False)
        except Exception:  # noqa: BLE001
            chunk = ""
        if chunk:
            chunks.append(chunk)
        if time.perf_counter() - started > args.timeout:
            timed_out = True
            subprocess.run(
                ["taskkill", "/PID", str(pty.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            break
        time.sleep(0.1)
    for _ in range(20):
        try:
            chunk = pty.read(8000, blocking=False)
        except Exception:  # noqa: BLE001
            chunk = ""
        if not chunk:
            break
        chunks.append(chunk)
    wall = time.perf_counter() - started
    poller.poll()
    poller.close()
    exit_code = pty.get_exitstatus()
    combined = "".join(chunks)
    text = strip_llama_logs(combined)
    text_path = out_dir / f"{sample.id}.{label}.txt"
    text_path.write_text(text + "\n", encoding="utf-8")
    raw_path = out_dir / f"{sample.id}.{label}.raw.log"
    raw_path.write_text(combined, encoding="utf-8", errors="replace")
    return {
        "sample_id": sample.id,
        "model_label": label,
        "model_path": str(model_path),
        "mmproj_path": str(mmproj_path),
        "command": command,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "wall_seconds": round(wall, 3),
        "stdout_bytes": len(combined.encode("utf-8", errors="replace")),
        "stderr_bytes": 0,
        "text_path": str(text_path),
        "raw_log_path": str(raw_path),
        "output": text,
        "perf": parse_perf(combined),
        "memory": poller.metrics(),
        "metrics": text_metrics(text, sample.baseline),
    }


def pairwise_metrics(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sample: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_sample.setdefault(result["sample_id"], []).append(result)
    pairs: list[dict[str, Any]] = []
    for sample_id, items in by_sample.items():
        for i, left in enumerate(items):
            for right in items[i + 1:]:
                pairs.append(
                    {
                        "sample_id": sample_id,
                        "left": left["model_label"],
                        "right": right["model_label"],
                        "sequence_ratio": rounded(
                            sequence_ratio(left["output"], right["output"])
                        ),
                        "cer_between_outputs": rounded(
                            error_rate(left["output"], right["output"], "char")
                        ),
                        "left_chars": len(left["output"]),
                        "right_chars": len(right["output"]),
                    }
                )
    return pairs


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        if value is None:
            return ""
        text = str(value)
        return text.replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        out.append("| " + " | ".join(cell(v) for v in row) + " |")
    return "\n".join(out)


def write_report(
    path: Path,
    args: argparse.Namespace,
    samples: list[Sample],
    results: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
) -> None:
    lines = [
        "# Dual OCR Benchmark",
        "",
        f"Run: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Working corpus: `{args.working}`",
        f"Runner: `{args.runner}`",
        "",
        "## Settings",
        "",
        markdown_table(
            ["setting", "value"],
            [
                ["ctx_size", args.ctx_size],
                ["predict", args.predict],
                ["threads", args.threads],
                ["threads_batch", args.threads_batch],
                ["cache_type_k", args.cache_type_k],
                ["cache_type_v", args.cache_type_v],
                ["image_max_tokens", args.image_max_tokens],
                ["image_min_tokens", args.image_min_tokens],
                ["gpu_layers", args.gpu_layers],
                ["temperature", args.temperature],
                ["seed", args.seed],
                ["log_verbosity", args.log_verbosity],
                ["timeout_seconds", args.timeout],
            ],
        ),
        "",
        "## Samples",
        "",
    ]
    sample_rows = []
    sample_by_id = {s.id: s for s in samples}
    for sample in samples:
        info = image_info(sample.image)
        sample_rows.append(
            [
                sample.id,
                sample.work,
                sample.page,
                sample.kind,
                info.get("width"),
                info.get("height"),
                info.get("bytes"),
                len(sample.baseline),
            ]
        )
    lines.append(
        markdown_table(
            ["id", "work", "page", "kind", "w", "h", "bytes", "baseline_chars"],
            sample_rows,
        )
    )
    lines.extend(["", "## Per-Run Metrics", ""])
    metric_rows = []
    for result in results:
        perf = result["perf"]
        mem = result["memory"]
        metrics = result["metrics"]
        metric_rows.append(
            [
                result["sample_id"],
                result["model_label"],
                result["exit_code"],
                result["timed_out"],
                result["wall_seconds"],
                mem.get("peak_working_set_mb"),
                perf.get("prompt_eval_tokens"),
                perf.get("eval_tokens"),
                perf.get("eval_tokens_per_second"),
                metrics.get("chars"),
                metrics.get("lines"),
                metrics.get("length_ratio_vs_baseline"),
                metrics.get("sequence_ratio_vs_baseline"),
                metrics.get("cer_vs_baseline"),
                metrics.get("latin_hint_rate"),
                metrics.get("unclear_count"),
                metrics.get("unclosed_think"),
                ",".join(metrics.get("meta_hits", [])),
            ]
        )
    lines.append(
        markdown_table(
            [
                "sample",
                "model",
                "exit",
                "timeout",
                "wall_s",
                "peak_ws_mb",
                "prompt_tok",
                "eval_tok",
                "eval_tps",
                "chars",
                "lines",
                "len_ratio",
                "seq_vs_base",
                "cer_vs_base",
                "latin_hint",
                "unclear",
                "unclosed_think",
                "meta_hits",
            ],
            metric_rows,
        )
    )
    lines.extend(["", "## Model Agreement", ""])
    lines.append(
        markdown_table(
            ["sample", "left", "right", "seq_ratio", "cer_between", "left_chars", "right_chars"],
            [
                [
                    pair["sample_id"],
                    pair["left"],
                    pair["right"],
                    pair["sequence_ratio"],
                    pair["cer_between_outputs"],
                    pair["left_chars"],
                    pair["right_chars"],
                ]
                for pair in pairs
            ],
        )
    )
    lines.extend(["", "## Output Excerpts", ""])
    for result in results:
        sample = sample_by_id[result["sample_id"]]
        excerpt = result["output"][:1500].strip()
        base_excerpt = sample.baseline[:1000].strip()
        lines.extend(
            [
                f"### {result['sample_id']} / {result['model_label']}",
                "",
                "**Model output**",
                "",
                "```text",
                excerpt,
                "```",
                "",
                "**Existing OCR baseline excerpt**",
                "",
                "```text",
                base_excerpt,
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_sample(value: str) -> dict[str, Any]:
    parts = value.split(":", 3)
    if len(parts) < 3:
        raise argparse.ArgumentTypeError(
            "sample must be id:work:page[:kind]"
        )
    return {
        "id": parts[0],
        "work": parts[1],
        "page": int(parts[2]),
        "kind": parts[3] if len(parts) > 3 else "",
    }


def resolve_models(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    models = DEFAULT_MODELS.copy()
    for item in args.model or []:
        label, model, mmproj = item.split(":", 2)
        models[label] = {"model": Path(model), "mmproj": Path(mmproj), "repo": ""}
    return models


def download_models(models: dict[str, dict[str, Any]]) -> None:
    for label, spec in models.items():
        repo = spec.get("repo")
        model = Path(spec["model"])
        mmproj = Path(spec["mmproj"])
        if model.exists() and mmproj.exists():
            print(f"[download] {label}: already present")
            continue
        if not repo:
            raise RuntimeError(f"Cannot auto-download custom model {label}")
        model.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "hf",
            "download",
            repo,
            "--include",
            model.name,
            "--include",
            mmproj.name,
            "--local-dir",
            str(model.parent),
        ]
        print("[download]", " ".join(cmd))
        subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--working", type=Path, default=DEFAULT_WORKING)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--runner", default="llama-mtmd-cli")
    parser.add_argument(
        "--use-pty",
        action=argparse.BooleanOptionalAction,
        default=(os.name == "nt"),
        help="Run llama-mtmd-cli inside a PTY on Windows so generation is emitted.",
    )
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--sample", type=parse_sample, action="append")
    parser.add_argument(
        "--model",
        action="append",
        help="Override/add a model as label:model_gguf:mmproj_gguf",
    )
    parser.add_argument("--only-model", action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ctx-size", type=int, default=4096)
    parser.add_argument("--predict", type=int, default=1800)
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--threads-batch", type=int, default=12)
    parser.add_argument("--cache-type-k", default="q4_0")
    parser.add_argument("--cache-type-v", default="q4_0")
    parser.add_argument("--image-max-tokens", type=int, default=1024)
    parser.add_argument("--image-min-tokens", type=int, default=1024)
    parser.add_argument("--gpu-layers", default="auto")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-verbosity", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    models = resolve_models(args)
    if args.only_model:
        wanted = set(args.only_model)
        models = {label: spec for label, spec in models.items() if label in wanted}
    if not models:
        raise SystemExit("No models selected")
    if args.download:
        download_models(models)

    missing = [
        str(path)
        for spec in models.values()
        for path in (Path(spec["model"]), Path(spec["mmproj"]))
        if not path.exists()
    ]
    if missing:
        raise SystemExit("Missing model files:\n" + "\n".join(missing))

    sample_defs = args.sample if args.sample else DEFAULT_SAMPLES
    if args.limit:
        sample_defs = sample_defs[: args.limit]
    samples = load_samples(args.working, sample_defs)
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = args.out_dir / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_meta = [
        {
            "id": sample.id,
            "work": sample.work,
            "page": sample.page,
            "kind": sample.kind,
            "image": image_info(sample.image),
            "baseline_chars": len(sample.baseline),
            "baseline_path": str(
                args.working / "data" / "corpus" / sample.work / "full.txt"
            ),
        }
        for sample in samples
    ]
    (out_dir / "samples.json").write_text(
        json.dumps(sample_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    results: list[dict[str, Any]] = []
    for sample in samples:
        for label, spec in models.items():
            print(f"[run] {sample.id} / {label}", flush=True)
            result = run_one(label, spec, sample, out_dir, args)
            results.append(result)
            slim = {k: v for k, v in result.items() if k != "output"}
            print(json.dumps(slim, ensure_ascii=False), flush=True)

    pairs = pairwise_metrics(results)
    write_jsonl(out_dir / "runs.jsonl", [{k: v for k, v in r.items() if k != "output"} for r in results])
    write_jsonl(out_dir / "agreement.jsonl", pairs)
    write_report(out_dir / "report.md", args, samples, results, pairs)
    print(f"[done] {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
