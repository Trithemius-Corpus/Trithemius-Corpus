"""Batch OCR Trithemius page images with Qwen3-VL-Instruct GGUF.

Outputs are written into the working corpus, not the release tree:

    E:/trithemius/data/corpus/<work>/translations/_reocr/<engine>/

The script is resume-safe and stitches per-page OCR into full.txt using the
same `--- Page NNN ---` convention as the existing corpus.
"""
from __future__ import annotations

import argparse
import atexit
import base64
import datetime as dt
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKING = Path(os.environ.get("TRITHEMIUS_WORKING", r"E:\trithemius"))
CORPUS = WORKING / "data" / "corpus"
LOGS = ROOT / ".cache" / "qwen3vl-ocr" / "logs"
CROPS = ROOT / ".cache" / "qwen3vl-ocr" / "crops"

MODEL_DIR = ROOT / ".cache" / "models" / "qwen3-vl-4b-instruct-q6"
MODEL = MODEL_DIR / "Qwen3-VL-4B-Instruct-Q6_K.gguf"
MMPROJ = MODEL_DIR / "mmproj-F16.gguf"
DEFAULT_ENGINE = "qwen3vl-4b-instruct-q6"
MAX_RAW_IMAGE_BYTES = 12_000_000
MAX_OCR_EDGE = 2400

OCR_PROMPT = """Transcribe this early-modern printed page faithfully.

Output only the page transcription. Do not translate, summarize, explain, or
describe the image.

Rules:
- Preserve visible line breaks where practical.
- Preserve headings, page numbers, marginal text, cipher strings, tables, and
  non-Latin words exactly as text.
- Normalize long-s to s, but otherwise keep early-modern spelling, v/u and i/j
  choices, punctuation, abbreviations, and capitalization as printed.
- Do not silently expand abbreviations. If a macron or abbreviation mark is
  visible and representable, preserve it; otherwise keep the abbreviated word.
- Use [unclear] for unreadable spans.
- Do not repeat [unclear] line after line. If a larger region is unreadable,
  write [large unreadable section] once and then continue with the next
  readable text.
- Stop after the visible page text. Do not fill blank or unreadable space with
  repeated uncertainty markers.
- If a page is blank or has no meaningful printed text, output [blank page].
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def image_data_url(image: Path) -> str:
    data = image.read_bytes()
    suffix = image.suffix.lower().lstrip(".")
    mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else "image/png"
    if len(data) <= MAX_RAW_IMAGE_BYTES:
        return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")

    try:
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = None
        with Image.open(image) as opened:
            opened.thumbnail((MAX_OCR_EDGE, MAX_OCR_EDGE), Image.Resampling.LANCZOS)
            if opened.mode not in {"RGB", "L"}:
                opened = opened.convert("RGB")
            buffer = io.BytesIO()
            opened.save(buffer, format="JPEG", quality=88, optimize=True)
            data = buffer.getvalue()
        return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
    except Exception:
        return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def crop_page_parts(image: Path, parts: int, overlap: int = 64) -> list[Path]:
    if parts <= 1:
        return [image]

    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    CROPS.mkdir(parents=True, exist_ok=True)
    out = []
    with Image.open(image) as opened:
        width, height = opened.size
        for index in range(parts):
            y0 = max(0, int(height * index / parts) - (overlap if index else 0))
            y1 = min(height, int(height * (index + 1) / parts) + (overlap if index + 1 < parts else 0))
            crop = opened.crop((0, y0, width, y1))
            if crop.mode not in {"RGB", "L"}:
                crop = crop.convert("RGB")
            path = CROPS / f"{image.parent.parent.name}_{image.stem}_part_{index + 1:02d}_of_{parts:02d}.jpg"
            crop.save(path, format="JPEG", quality=92, optimize=True)
            out.append(path)
    return out


def find_free_port(start: int = 8091) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free localhost port found")


def llama_server_bin() -> str:
    return shutil.which("llama-server") or "llama-server"


def extract_ocr_section(text: str) -> str:
    cleaned = text.strip()
    match = re.search(r"(?im)^\s*OCR\s*:\s*", cleaned)
    if match:
        cleaned = cleaned[match.end() :]
    end = re.search(r"(?im)^\s*EN\s*:\s*", cleaned)
    if end:
        cleaned = cleaned[: end.start()]
    cleaned = re.sub(r"(?m)^```[a-zA-Z0-9_-]*\s*$", "", cleaned)
    cleaned = re.sub(r"(?m)^```\s*$", "", cleaned)
    return cleaned.strip()


def infer_gguf(path: Path, *, mmproj: bool) -> Path:
    pattern = "*.gguf"
    if not path.exists():
        raise FileNotFoundError(path)
    lowered = []
    for candidate in sorted(path.glob(pattern)):
        name = candidate.name.lower()
        is_mmproj = name.startswith("mmproj") or "mmproj" in name
        if is_mmproj == mmproj:
            lowered.append(candidate)
    if len(lowered) == 1:
        return lowered[0]
    kind = "mmproj" if mmproj else "model"
    names = ", ".join(candidate.name for candidate in lowered) or "none"
    raise SystemExit(f"Could not infer {kind} GGUF in {path}; candidates: {names}")


def resolve_model_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.model_dir:
        model_dir = args.model_dir
        model = args.model or infer_gguf(model_dir, mmproj=False)
        mmproj = args.mmproj or infer_gguf(model_dir, mmproj=True)
        return model, mmproj
    return args.model or MODEL, args.mmproj or MMPROJ


class QwenServer:
    def __init__(
        self,
        *,
        model: Path = MODEL,
        mmproj: Path = MMPROJ,
        port: int | None = None,
        ctx_size: int = 8192,
        max_tokens: int = 3200,
        parallel: int = 1,
        image_tokens: int = 1024,
        no_mmproj_offload: bool = False,
        prompt: str = OCR_PROMPT,
        startup_timeout: int = 240,
    ) -> None:
        self.model = model
        self.mmproj = mmproj
        self.port = port or find_free_port()
        self.ctx_size = ctx_size
        self.max_tokens = max_tokens
        self.parallel = parallel
        self.image_tokens = image_tokens
        self.no_mmproj_offload = no_mmproj_offload
        self.prompt = prompt
        self.startup_timeout = startup_timeout
        self.proc: subprocess.Popen[str] | None = None
        self.log_fh = None
        self.log_path: Path | None = None

    def __enter__(self) -> "QwenServer":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

    def start(self) -> None:
        if not self.model.exists():
            raise FileNotFoundError(self.model)
        if not self.mmproj.exists():
            raise FileNotFoundError(self.mmproj)
        LOGS.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_path = LOGS / f"llama-server-{stamp}-{self.port}.log"
        self.log_fh = self.log_path.open("w", encoding="utf-8")
        cmd = [
            llama_server_bin(),
            "--model",
            str(self.model),
            "--mmproj",
            str(self.mmproj),
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--ctx-size",
            str(self.ctx_size),
            "--parallel",
            str(self.parallel),
            "--gpu-layers",
            "auto",
            "--cache-type-k",
            "q4_0",
            "--cache-type-v",
            "q4_0",
            "--image-min-tokens",
            str(self.image_tokens),
            "--image-max-tokens",
            str(self.image_tokens),
            "--no-webui",
            "--no-warmup",
            "--log-colors",
            "off",
            "--log-verbosity",
            "2",
        ]
        if self.no_mmproj_offload:
            cmd.append("--no-mmproj-offload")
        print(f"[server] starting port={self.port} log={self.log_path}", flush=True)
        self.proc = subprocess.Popen(
            cmd,
            stdout=self.log_fh,
            stderr=subprocess.STDOUT,
            cwd=str(ROOT),
            text=True,
        )
        atexit.register(self.kill_quietly)
        self.wait_ready()

    def wait_ready(self) -> None:
        assert self.proc is not None
        url = f"http://127.0.0.1:{self.port}/v1/models"
        deadline = time.time() + self.startup_timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"llama-server exited with {self.proc.returncode}; see {self.log_path}"
                )
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        print("[server] ready", flush=True)
                        return
            except (OSError, urllib.error.URLError):
                time.sleep(1)
        raise TimeoutError(f"llama-server did not become ready; see {self.log_path}")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.log_fh:
            self.log_fh.close()
            self.log_fh = None

    def kill_quietly(self) -> None:
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.kill()
        except Exception:
            pass

    def ocr_page(
        self,
        image: Path,
        *,
        timeout: int = 900,
        part_index: int | None = None,
        part_count: int | None = None,
    ) -> tuple[str, float, dict[str, Any]]:
        prompt = self.prompt
        if part_index and part_count:
            prompt += (
                f"\nThis image is crop part {part_index} of {part_count}, ordered "
                "from top to bottom. Transcribe only the visible text in this crop."
            )
        payload = {
            "model": "qwen3vl",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url(image)
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            elapsed = time.time() - started
            obj = json.loads(body)
            text = obj["choices"][0]["message"]["content"].strip()
            return text, elapsed, obj.get("usage", {})
        except Exception as exc:  # noqa: BLE001
            elapsed = time.time() - started
            return f"[ERROR server: {type(exc).__name__}: {exc}]", elapsed, {}

    def ocr_page_split(
        self,
        image: Path,
        *,
        parts: int,
        timeout: int = 900,
    ) -> tuple[str, float, dict[str, Any]]:
        texts = []
        total_seconds = 0.0
        part_usages = []
        for index, crop in enumerate(crop_page_parts(image, parts), 1):
            text, seconds, usage = self.ocr_page(
                crop,
                timeout=timeout,
                part_index=index,
                part_count=parts,
            )
            total_seconds += seconds
            part_usages.append(usage)
            if text.startswith("[ERROR"):
                return text, total_seconds, {"parts": part_usages}
            texts.append(text)
        usage_totals: dict[str, Any] = {"parts": part_usages, "split_parts": parts}
        for key in ("completion_tokens", "prompt_tokens", "total_tokens"):
            values = [usage.get(key) for usage in part_usages if isinstance(usage.get(key), int)]
            if values:
                usage_totals[key] = sum(values)
        return "\n".join(part.strip() for part in texts if part.strip()), total_seconds, usage_totals


def real_work_dirs() -> list[Path]:
    out = []
    for work_dir in sorted(CORPUS.iterdir()):
        if not work_dir.is_dir() or work_dir.name.startswith("_"):
            continue
        if (work_dir / "pages").is_dir():
            out.append(work_dir)
    return out


def page_files(work_dir: Path) -> list[Path]:
    return sorted((work_dir / "pages").glob("page_*.png"))


def work_summary() -> list[dict[str, Any]]:
    rows = []
    for work_dir in real_work_dirs():
        pages = page_files(work_dir)
        full = work_dir / "full.txt"
        rows.append(
            {
                "work": work_dir.name,
                "pages": len(pages),
                "full_chars": full.stat().st_size if full.exists() else 0,
            }
        )
    return sorted(rows, key=lambda r: (r["pages"], r["work"]))


def out_root(work_id: str, engine: str) -> Path:
    return CORPUS / work_id / "translations" / "_reocr" / engine


def is_done(page_txt: Path) -> bool:
    if not page_txt.exists() or page_txt.stat().st_size == 0:
        return False
    return not read_text(page_txt).startswith("[ERROR")


def page_num(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def stitch(work_id: str, pages: list[Path], engine: str) -> Path:
    root = out_root(work_id, engine)
    lines: list[str] = []
    for image in pages:
        num = page_num(image)
        txt = root / f"page_{num:03d}.txt"
        text = read_text(txt).strip() if txt.exists() else ""
        if text.startswith("[ERROR"):
            text = ""
        lines.append(f"--- Page {num:03d} ---")
        lines.append("")
        lines.append(text)
        lines.append("")
    full = root / "full.txt"
    write_text(full, "\n".join(lines).rstrip() + "\n")
    return full


def run_work(server: QwenServer, work_id: str, args: argparse.Namespace) -> dict[str, Any]:
    work_dir = CORPUS / work_id
    all_pages = page_files(work_dir)
    pages = all_pages
    if args.start_page:
        pages = [p for p in pages if page_num(p) >= args.start_page]
    if args.end_page:
        pages = [p for p in pages if page_num(p) <= args.end_page]
    if args.pages:
        wanted = {int(x.strip()) for x in args.pages.split(",") if x.strip()}
        pages = [p for p in pages if page_num(p) in wanted]
    if args.max_pages:
        pages = pages[: args.max_pages]
    root = out_root(work_id, args.engine)
    root.mkdir(parents=True, exist_ok=True)
    metrics_path = root / "qwen3vl_page_metrics.jsonl"
    pending = []
    for image in pages:
        txt = root / f"page_{page_num(image):03d}.txt"
        if args.force or not is_done(txt):
            pending.append(image)
    print(
        f"\n=== OCR {work_id}: pages={len(pages)} pending={len(pending)} out={root} ===",
        flush=True,
    )
    started = time.time()
    done = skipped = failed = 0
    for i, image in enumerate(pending, 1):
        num = page_num(image)
        if args.split_parts > 1:
            text, secs, usage = server.ocr_page_split(
                image,
                parts=args.split_parts,
                timeout=args.page_timeout,
            )
        else:
            text, secs, usage = server.ocr_page(image, timeout=args.page_timeout)
        if args.extract_ocr_section and not text.startswith("[ERROR"):
            text = extract_ocr_section(text)
        completion_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
        part_usages = usage.get("parts", []) if isinstance(usage, dict) else []
        capped = isinstance(completion_tokens, int) and completion_tokens >= server.max_tokens
        capped = capped or any(
            isinstance(part.get("completion_tokens"), int)
            and part["completion_tokens"] >= server.max_tokens
            for part in part_usages
            if isinstance(part, dict)
        )
        write_text(root / f"page_{num:03d}.txt", text.rstrip() + "\n")
        failed += int(text.startswith("[ERROR"))
        done += 1
        record = {
            "work": work_id,
            "engine": args.engine,
            "page": num,
            "image": str(image),
            "chars": len(text),
            "seconds": round(secs, 3),
            "error": text.startswith("[ERROR"),
            "capped": capped,
            "max_tokens": server.max_tokens,
            "split_parts": args.split_parts,
            "model": str(server.model),
            "mmproj": str(server.mmproj),
            "usage": usage,
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        }
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        elapsed = time.time() - started
        rate = elapsed / max(done, 1)
        eta = rate * (len(pending) - i)
        status = ""
        if text.startswith("[ERROR"):
            status = " (error)"
        elif capped:
            status = " (capped)"
        print(
            f"  [{i:3}/{len(pending)}] page {num:03d}: {len(text):>5} chars "
            f"{secs:6.1f}s total {elapsed/60:5.1f}m ETA {eta/60:5.1f}m "
            f"{status}",
            flush=True,
        )
    skipped = len(pages) - len(pending)
    full = stitch(work_id, all_pages, args.engine)
    elapsed = time.time() - started
    print(
        f"=== DONE {work_id}: ocred={done} skipped={skipped} failed={failed} "
        f"elapsed={elapsed/60:.1f}m full={full} ({full.stat().st_size:,} bytes) ===",
        flush=True,
    )
    return {
        "work": work_id,
        "engine": args.engine,
        "pages": len(pages),
        "ocred": done,
        "skipped": skipped,
        "failed": failed,
        "full": str(full),
        "elapsed_seconds": round(elapsed, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", action="append", help="Work id to OCR; repeatable.")
    parser.add_argument("--smallest", type=int, help="OCR the N smallest works.")
    parser.add_argument("--list-smallest", type=int, metavar="N")
    parser.add_argument("--start-page", type=int)
    parser.add_argument("--end-page", type=int)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--pages", type=str,
                        help="Comma-separated explicit page numbers to OCR (e.g. 15,51,100). "
                             "Intersected with start/end-page range. Use with --force.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--engine", default=DEFAULT_ENGINE)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--mmproj", type=Path)
    parser.add_argument("--no-mmproj-offload", action="store_true")
    parser.add_argument("--prompt", default=OCR_PROMPT)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--extract-ocr-section", action="store_true")
    parser.add_argument("--ctx-size", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=3200)
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--image-tokens", type=int, default=1024)
    parser.add_argument("--split-parts", type=int, default=1)
    parser.add_argument("--page-timeout", type=int, default=900)
    parser.add_argument("--port", type=int)
    args = parser.parse_args()

    if args.list_smallest:
        for row in work_summary()[: args.list_smallest]:
            print(f"{row['pages']:4} pages  {row['full_chars']:8} bytes  {row['work']}")
        return 0

    works = args.work or []
    if args.smallest:
        works.extend(row["work"] for row in work_summary()[: args.smallest])
    # Preserve order while removing duplicates.
    works = list(dict.fromkeys(works))
    if not works:
        raise SystemExit("Pass --work WORK_ID, --smallest N, or --list-smallest N")

    if args.prompt_file:
        args.prompt = read_text(args.prompt_file)
    model, mmproj = resolve_model_paths(args)
    run_summary = []
    with QwenServer(
        model=model,
        mmproj=mmproj,
        port=args.port,
        ctx_size=args.ctx_size,
        max_tokens=args.max_tokens,
        parallel=args.parallel,
        image_tokens=args.image_tokens,
        no_mmproj_offload=args.no_mmproj_offload,
        prompt=args.prompt,
    ) as server:
        for work_id in works:
            run_summary.append(run_work(server, work_id, args))

    summary_path = ROOT / ".cache" / "qwen3vl-ocr" / "last_run_summary.json"
    write_text(summary_path, json.dumps(run_summary, indent=2, ensure_ascii=False))
    print(f"\nWrote summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
