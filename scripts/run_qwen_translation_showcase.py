"""Run the Qwen translator over the 6 PRD works and report per-work totals.

This is the production pass for the trithemius-corpus codex-vs-qwen
translation showcase. It invokes translate_with_qwen.py per work.

Usage:
    python scripts/run_qwen_translation_showcase.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
TRANSLATE_SCRIPT = ROOT / "scripts" / "translate_with_qwen.py"

PRD_WORKS = [
    "prdl-24376_ecloga-de-laude-calvorum-ad-carolum",
    "prdl-24364_de-laudibus-sanctissimae-matris-annae",
    "prdl-70284_de-laudibus-sanctissimae-matris-annae",
    "prdl-70283_de-laudibus-sancctissime-matris-anne-tractat",
    "prdl-24370_de-purissima-et-immaculata-conceptione-virginis",
    "prdl-24369_de-purissima-et-immaculata-conceptione-virginis",
]
OUT_BACKEND = "qwen3vl-trithemius-q6-translator-qwen"
SERVER_URL = "http://127.0.0.1:8080"


def main() -> int:
    overall_t0 = time.time()
    summaries = []
    for work in PRD_WORKS:
        print(f"\n===== {work} =====")
        t0 = time.time()
        proc = subprocess.run(
            [
                PYTHON, str(TRANSLATE_SCRIPT),
                "--work", work,
                "--server-url", SERVER_URL,
                "--out-backend", OUT_BACKEND,
                "--max-chars", "4500",
                "--max-tokens", "2000",
                "--temperature", "0.2",
                "--top-p", "0.6",
                "--timeout", "600",
            ],
            cwd=str(ROOT),
        )
        elapsed = time.time() - t0
        summaries.append((work, proc.returncode, elapsed))
        print(f"--- {work} done in {elapsed:.1f}s, exit={proc.returncode} ---")
    total = time.time() - overall_t0
    print("\n===== SUMMARY =====")
    for w, rc, e in summaries:
        print(f"  exit={rc}  {e:6.1f}s  {w}")
    print(f"Total: {total:.1f}s ({total/60:.1f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
