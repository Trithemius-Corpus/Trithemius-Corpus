"""Run one Vast shard of Trithemius page OCR with a Qwen3-VL GGUF model.

The shard is produced by `build_qwen3vl_vast_reocr_payload.py`. Model files are
not bundled; put the Q6 GGUF and F16 mmproj on the worker and pass their paths.
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
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
DEFAULT_ENGINE = "qwen3vl-4b-trithemius-q6"
DEFAULT_MODEL = Path(os.environ.get("QWEN3VL_MODEL", "/workspace/models/Qwen3-VL-4B-Trithemius-Q6_K.gguf"))
DEFAULT_MMPROJ = Path(os.environ.get("QWEN3VL_MMPROJ", "/workspace/models/mmproj-Qwen3-VL-4B-Trithemius-F16.gguf"))
MAX_RAW_IMAGE_BYTES = 12_000_000
MAX_OCR_EDGE = 2400

OCR_ONLY_PROMPT = """Transcribe this early-modern printed page faithfully.

Output only the Latin transcription under OCR:. Do not translate, summarize,
explain, or describe the image.

Rules:
- Preserve visible line breaks where practical.
- Preserve headings, page numbers, marginal text, cipher strings, tables, and
  non-Latin words exactly as text.
- Normalize long-s to s, but otherwise keep early-modern spelling, v/u and i/j
  choices, punctuation, abbreviations, and capitalization as printed.
- Do not silently expand abbreviations.
- Use [unclear] for unreadable spans.
- Do not repeat [unclear] line after line. If a larger region is unreadable,
  write [large unreadable section] once and then continue with the next
  readable text.
- If a page is blank or has no meaningful printed text, output [blank page].
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def load_targets(path: Path) -> dict[str, Any]:
    data = json.loads(read_text(path))
    if not isinstance(data, dict) or not isinstance(data.get("pages"), list):
        raise SystemExit("Targets JSON must be an object with a pages list.")
    return data


def llama_server_bin() -> str:
    return shutil.which("llama-server") or "llama-server"


def find_free_port(start: int = 8091) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free localhost port found")


def image_data_url(image: Path) -> str:
    data = image.read_bytes()
    suffix = image.suffix.lower().lstrip(".")
    mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else "image/png"
    if len(data) <= MAX_RAW_IMAGE_BYTES:
        return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")

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


class QwenServer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.model = args.model
        self.mmproj = args.mmproj
        self.port = args.port or find_free_port()
        self.ctx_size = args.ctx_size
        self.max_tokens = args.max_tokens
        self.image_tokens = args.image_tokens
        self.no_mmproj_offload = args.no_mmproj_offload
        self.parallel = getattr(args, "parallel", 1)
        self.cont_batching = getattr(args, "cont_batching", False)
        self.kv_cache = getattr(args, "kv_cache", "f16")
        self.attach = getattr(args, "attach", False)  # attach to an already-running server
        self.proc: subprocess.Popen[str] | None = None
        self.log_fh = None
        self.log_path: Path | None = None

    def __enter__(self) -> "QwenServer":
        if self.attach:
            self.wait_ready()  # connect to an externally-managed server
        else:
            self.start()
        return self

    def __exit__(self, *args: object) -> None:
        if not self.attach:
            self.stop()
        # When attaching, leave the server running for other clients.

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
            "--model", str(self.model),
            "--mmproj", str(self.mmproj),
            "--host", "127.0.0.1",
            "--port", str(self.port),
            "--ctx-size", str(self.ctx_size),
            "--parallel", str(self.parallel),
            "--gpu-layers", "auto",
            "--image-min-tokens", str(self.image_tokens),
            "--image-max-tokens", str(self.image_tokens),
            "--no-webui",
            "--log-colors", "off",
            "--log-verbosity", "2",
        ]
        # KV cache type: f16 is faster and VRAM is plentiful at ~4GB/24GB used.
        # q4_0 saves VRAM at a speed cost we don't need to pay.
        if self.kv_cache and self.kv_cache != "f16":
            cmd += ["--cache-type-k", self.kv_cache, "--cache-type-v", self.kv_cache]
        if self.cont_batching:
            cmd.append("--cont-batching")
        if self.no_mmproj_offload:
            cmd.append("--no-mmproj-offload")
        print(f"[server] starting port={self.port} log={self.log_path}", flush=True)
        self.proc = subprocess.Popen(cmd, stdout=self.log_fh, stderr=subprocess.STDOUT, text=True)
        atexit.register(self.kill_quietly)
        self.wait_ready()

    def wait_ready(self) -> None:
        url = f"http://127.0.0.1:{self.port}/v1/models"
        deadline = time.time() + 240
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise RuntimeError(f"llama-server exited with {self.proc.returncode}; see {self.log_path}")
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        print(f"[server] ready port={self.port}", flush=True)
                        return
            except (OSError, urllib.error.URLError):
                time.sleep(1)
        raise TimeoutError(
            f"llama-server did not become ready at port={self.port}"
            + (f"; see {self.log_path}" if self.log_path else "")
        )

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.log_fh:
            self.log_fh.close()

    def kill_quietly(self) -> None:
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.kill()
        except Exception:
            pass

    def ocr_page(self, image: Path, prompt: str, timeout: int) -> tuple[str, float, dict[str, Any]]:
        payload = {
            "model": "qwen3vl",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_url(image)}},
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
                obj = json.loads(response.read().decode("utf-8"))
            text = obj["choices"][0]["message"]["content"].strip()
            return text, time.time() - started, obj.get("usage", {})
        except Exception as exc:  # noqa: BLE001
            return f"[ERROR server: {type(exc).__name__}: {exc}]", time.time() - started, {}


def is_done(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0 and not read_text(path).startswith("[ERROR")


def run(args: argparse.Namespace) -> dict[str, Any]:
    targets = load_targets(args.targets)
    engine = args.engine or targets.get("engine") or DEFAULT_ENGINE
    prompt = read_text(args.prompt_file) if args.prompt_file else OCR_ONLY_PROMPT
    output_root = args.output_root / engine
    output_root.mkdir(parents=True, exist_ok=True)
    raw_root = output_root / "_raw"
    metrics_path = output_root / f"metrics_{args.worker_id}.jsonl"
    pages = targets["pages"]
    done = failed = skipped = 0
    started = time.time()
    print(f"[worker] pages={len(pages)} engine={engine} output={output_root}", flush=True)
    with QwenServer(args) as server:
        for index, row in enumerate(pages, 1):
            work = str(row["work"])
            page = int(row["page"])
            image = ROOT / str(row["image"])
            out = output_root / work / f"page_{page:03d}.txt"
            if not args.force and is_done(out):
                skipped += 1
                continue
            raw, seconds, usage = server.ocr_page(image, prompt, args.page_timeout)
            text = raw if raw.startswith("[ERROR") else extract_ocr_section(raw)
            write_text(out, text.rstrip() + "\n")
            if args.write_raw:
                write_text(raw_root / work / f"page_{page:03d}.txt", raw.rstrip() + "\n")
            completion_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
            capped = isinstance(completion_tokens, int) and completion_tokens >= server.max_tokens
            error = text.startswith("[ERROR")
            failed += int(error)
            done += 1
            with metrics_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "work": work,
                    "engine": engine,
                    "page": page,
                    "image": str(image),
                    "output": str(out),
                    "chars": len(text),
                    "raw_chars": len(raw),
                    "seconds": round(seconds, 3),
                    "error": error,
                    "capped": capped,
                    "max_tokens": server.max_tokens,
                    "model": str(server.model),
                    "mmproj": str(server.mmproj),
                    "usage": usage,
                    "worker_id": args.worker_id,
                    "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
                }, ensure_ascii=False) + "\n")
            elapsed = time.time() - started
            rate = elapsed / max(done, 1)
            eta = rate * (len(pages) - index)
            suffix = " error" if error else " capped" if capped else ""
            print(
                f"[{index:4}/{len(pages)}] {work} page {page:03d}: "
                f"{len(text):5} chars {seconds:6.1f}s ETA {eta/60:5.1f}m{suffix}",
                flush=True,
            )
    summary = {
        "worker_id": args.worker_id,
        "engine": engine,
        "pages": len(pages),
        "ocred": done,
        "skipped": skipped,
        "failed": failed,
        "elapsed_seconds": round(time.time() - started, 3),
        "output_root": str(output_root),
        "metrics": str(metrics_path),
    }
    summary_path = output_root / f"summary_{args.worker_id}.json"
    write_text(summary_path, json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(f"[worker] wrote {summary_path}", flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=Path, default=ROOT / "targets.json")
    parser.add_argument("--engine")
    parser.add_argument("--worker-id", default=os.environ.get("WORKER_ID", "worker"))
    parser.add_argument("--output-root", type=Path, default=ROOT / "ocr_outputs")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--mmproj", type=Path, default=DEFAULT_MMPROJ)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--write-raw", action="store_true", default=True)
    parser.add_argument("--ctx-size", type=int, default=8192)
    parser.add_argument("--max-tokens", type=int, default=3000)
    parser.add_argument("--image-tokens", type=int, default=1024)
    parser.add_argument("--page-timeout", type=int, default=900)
    parser.add_argument("--port", type=int)
    parser.add_argument(
        "--parallel", type=int, default=1,
        help="llama-server --parallel slots (concurrent request capacity).",
    )
    parser.add_argument(
        "--cont-batching", action="store_true",
        help="Enable llama-server continuous batching across slots.",
    )
    parser.add_argument(
        "--kv-cache", default="f16", choices=("f16", "q8_0", "q4_0"),
        help="KV cache quant. f16 is fastest; VRAM is plentiful at ~4GB/24GB used.",
    )
    parser.add_argument(
        "--attach", action="store_true",
        help="Attach to an already-running llama-server at --port instead of launching one. "
             "Used when multiple client processes share one batching server per GPU.",
    )
    parser.set_defaults(no_mmproj_offload=True)
    parser.add_argument("--no-mmproj-offload", dest="no_mmproj_offload", action="store_true")
    parser.add_argument("--mmproj-offload", dest="no_mmproj_offload", action="store_false")
    return parser.parse_args()


def main() -> int:
    run(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
