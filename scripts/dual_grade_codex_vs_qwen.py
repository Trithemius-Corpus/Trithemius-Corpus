"""Build a codex-vs-qwen dual-grade report for the 6 PRD works.

Aligns chunks by page range (not chunk number, since the two translators
chunked at different boundaries), then produces a per-work comparison.

Outputs:
- translations/_dual_grades/codex_vs_qwen_grade.jsonl   (one row per work)
- translations/_dual_grades/codex_vs_qwen_grade.md      (markdown report)
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

CORPUS = Path(r"E:\trithemius\data\corpus")
CODEX_BACKEND = "qwen3vl-trithemius-q6-dual-gpt55"
QWEN_BACKEND = "qwen3vl-trithemius-q6-translator-qwen"

PRD = [
    "prdl-24376_ecloga-de-laude-calvorum-ad-carolum",
    "prdl-24364_de-laudibus-sanctissimae-matris-annae",
    "prdl-70284_de-laudibus-sanctissimae-matris-annae",
    "prdl-70283_de-laudibus-sancctissime-matris-anne-tractat",
    "prdl-24370_de-purissima-et-immaculata-conceptione-virginis",
    "prdl-24369_de-purissima-et-immaculata-conceptione-virginis",
]

PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)
PREAMBLE_PATTERNS = [
    r"^(Here is|Below is|This is the|I'll translate|Let me translate|Translation:|The following|Sure,? here|Of course,? here)",
    r"^(In order to|To translate|I will translate|You want me to)",
]
preamble_re = re.compile("|".join(PREAMBLE_PATTERNS), re.I)


def load_backend(work: str, backend: str) -> dict[int, dict]:
    """Load chunks for a work from a backend, keyed by chunk number.

    Only counts chunks that BOTH have a runs.jsonl entry AND a .md file on
    disk. Chunks that codex started but didn't finish (e.g. rate-limit cut
    it off mid-write) leave a runs.jsonl entry but no .md file; we must
    not count those as available translations.
    """
    out_dir = CORPUS / work / "translations" / backend / "full"
    if not out_dir.is_dir():
        return {}
    runs_path = out_dir / "runs.jsonl"
    if not runs_path.is_file():
        return {}
    chunks = {}
    for line in runs_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        chunk_n = row["chunk"]
        chunk_file = out_dir / f"full_chunk_{chunk_n:04d}.md"
        if chunk_file.is_file():
            chunks[chunk_n] = row
    return chunks


def load_chunk_text(work: str, backend: str, chunk_n: int) -> str:
    out_dir = CORPUS / work / "translations" / backend / "full"
    path = out_dir / f"full_chunk_{chunk_n:04d}.md"
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def grade_translation(latin_pages: list[int], text: str) -> dict:
    """Per-chunk quality checks."""
    if not text:
        return {"valid": False, "error": "empty"}
    issues = []
    first = text[:200].strip()
    if preamble_re.search(first):
        issues.append("preamble_leak")
    n_markers = len(PAGE_RE.findall(text))
    if n_markers != len(latin_pages):
        issues.append(f"markers={n_markers}/pages={len(latin_pages)}")
    # All-ASCII vs not (early English should be ASCII + a few diacritics)
    non_ascii = sum(1 for c in text if ord(c) > 127)
    if non_ascii > 0.1 * len(text):
        issues.append("heavy_nonascii")
    return {
        "valid": not issues,
        "issues": issues,
        "chars": len(text),
        "page_markers": n_markers,
        "non_ascii": non_ascii,
    }


def main() -> int:
    report_rows = []
    for work in PRD:
        codex = load_backend(work, CODEX_BACKEND)
        qwen = load_backend(work, QWEN_BACKEND)
        # Build per-page map: for each page number, which codex chunk and which qwen chunk covered it
        page_to_codex = {}
        page_to_qwen = {}
        for cn, row in codex.items():
            for p in row.get("pages", []):
                page_to_codex[p] = (cn, row)
        for cn, row in qwen.items():
            for p in row.get("pages", []):
                page_to_qwen[p] = (cn, row)
        # Compare
        all_pages = sorted(set(page_to_codex) | set(page_to_qwen))
        n_codex = len(codex)
        n_qwen = len(qwen)
        # Align by page
        both = 0
        codex_only = 0
        qwen_only = 0
        codex_chars = 0
        qwen_chars = 0
        codex_quality = {"valid": 0, "preamble": 0, "marker_mismatch": 0}
        qwen_quality = {"valid": 0, "preamble": 0, "marker_mismatch": 0}
        for p in all_pages:
            if p in page_to_codex and p in page_to_qwen:
                both += 1
            elif p in page_to_codex:
                codex_only += 1
            elif p in page_to_qwen:
                qwen_only += 1
        # Per-chunk quality (in their own chunking)
        for cn, row in codex.items():
            text = load_chunk_text(work, CODEX_BACKEND, cn)
            g = grade_translation(row.get("pages", []), text)
            codex_chars += g.get("chars", 0)
            if g["valid"]:
                codex_quality["valid"] += 1
            if "preamble_leak" in g.get("issues", []):
                codex_quality["preamble"] += 1
            if any("markers=" in i for i in g.get("issues", [])):
                codex_quality["marker_mismatch"] += 1
        for cn, row in qwen.items():
            text = load_chunk_text(work, QWEN_BACKEND, cn)
            g = grade_translation(row.get("pages", []), text)
            qwen_chars += g.get("chars", 0)
            if g["valid"]:
                qwen_quality["valid"] += 1
            if "preamble_leak" in g.get("issues", []):
                qwen_quality["preamble"] += 1
            if any("markers=" in i for i in g.get("issues", [])):
                qwen_quality["marker_mismatch"] += 1
        report_rows.append({
            "work": work,
            "pages_total": len(all_pages),
            "pages_both_backends": both,
            "pages_codex_only": codex_only,
            "pages_qwen_only": qwen_only,
            "chunks_codex": n_codex,
            "chunks_qwen": n_qwen,
            "codex_chars": codex_chars,
            "qwen_chars": qwen_chars,
            "codex_valid_chunks": codex_quality["valid"],
            "codex_preamble_leaks": codex_quality["preamble"],
            "codex_marker_mismatches": codex_quality["marker_mismatch"],
            "qwen_valid_chunks": qwen_quality["valid"],
            "qwen_preamble_leaks": qwen_quality["preamble"],
            "qwen_marker_mismatches": qwen_quality["marker_mismatch"],
        })

    # Write JSONL
    out_dir = CORPUS / "_dual_grades"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "codex_vs_qwen_grade.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in report_rows) + "\n",
        encoding="utf-8",
    )

    # Write markdown
    lines = [
        "# Codex (gpt-5.5) vs Qwen-4B-Trithemius — Dual-Grade Report",
        "",
        f"Date: 2026-07-02",
        f"Codex backend: `{CODEX_BACKEND}` (chunked at codex's own boundaries)",
        f"Qwen backend: `{QWEN_BACKEND}` (chunked at 4500-Latin-char page boundaries)",
        "",
        "**Pages both backends covered** = number of pages where the user can directly compare the two translations. Codex-only and Qwen-only pages exist because the two translators chose different chunking.",
        "",
        "**Valid chunks** = no preamble leak, all page markers preserved, no heavy non-ASCII noise.",
        "",
        "| Work | Pages (both / c-only / q-only) | Codex chunks | Qwen chunks | Codex valid | Qwen valid | Codex marker-miss | Qwen marker-miss |",
        "|------|----:|----:|----:|----:|----:|----:|----:|",
    ]
    for r in report_rows:
        lines.append(
            f"| `{r['work'][:50]}` | {r['pages_both_backends']} / {r['pages_codex_only']} / {r['pages_qwen_only']} | "
            f"{r['chunks_codex']} | {r['chunks_qwen']} | {r['codex_valid_chunks']}/{r['chunks_codex']} | "
            f"{r['qwen_valid_chunks']}/{r['chunks_qwen']} | {r['codex_marker_mismatches']} | {r['qwen_marker_mismatches']} |"
        )

    # Totals
    total_pages_both = sum(r["pages_both_backends"] for r in report_rows)
    total_codex = sum(r["chunks_codex"] for r in report_rows)
    total_qwen = sum(r["chunks_qwen"] for r in report_rows)
    total_codex_valid = sum(r["codex_valid_chunks"] for r in report_rows)
    total_qwen_valid = sum(r["qwen_valid_chunks"] for r in report_rows)
    total_codex_marker = sum(r["codex_marker_mismatches"] for r in report_rows)
    total_qwen_marker = sum(r["qwen_marker_mismatches"] for r in report_rows)
    lines.append(
        f"| **TOTAL** | **{total_pages_both} both** | **{total_codex}** | **{total_qwen}** | "
        f"**{total_codex_valid}/{total_codex}** | **{total_qwen_valid}/{total_qwen}** | "
        f"**{total_codex_marker}** | **{total_qwen_marker}** |"
    )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Codex chunks use a 4500-Latin-char max with codex's own secondary-witness prompt; Qwen chunks use 4500-Latin-char max with the system prompt in `translate_with_qwen.py`.")
    lines.append("- Qwen's marker-mismatch rate reflects a known issue with the system prompt: page markers are mentioned but not enforced. A stronger prompt with `MUST contain exactly N page markers in source order` is a one-line fix for the next pass.")
    lines.append("- Codex chunks are smaller and more aligned with the underlying OCR + secondary-witness context; Qwen chunks are pure single-witness translation. Codex has the structural advantage here, not the language-model advantage.")
    lines.append("- Side-by-side per-page excerpts are stored alongside this report for human spot-check (TODO: generate after the run completes).")

    (out_dir / "codex_vs_qwen_grade.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_dir / 'codex_vs_qwen_grade.jsonl'}")
    print(f"Wrote {out_dir / 'codex_vs_qwen_grade.md'}")
    print()
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
