"""Generate per-page side-by-side excerpts for human spot-check.

For each page that both backends covered, extract the relevant
text from each backend's translation and write a markdown
file with aligned excerpts.
"""
from __future__ import annotations

import re
from pathlib import Path

CORPUS = Path(r"E:\trithemius\data\corpus")
CODEX = "qwen3vl-trithemius-q6-dual-gpt55"
QWEN = "qwen3vl-trithemius-q6-translator-qwen"

PRD = [
    ("prdl-24376_ecloga-de-laude-calvorum-ad-carolum", "Ecloga de laude calvorum"),
    ("prdl-24364_de-laudibus-sanctissimae-matris-annae", "De laudibus Annae (small)"),
    ("prdl-70284_de-laudibus-sanctissimae-matris-annae", "De laudibus Annae (large)"),
    ("prdl-70283_de-laudibus-sancctissime-matris-anne-tractat", "De laudibus Annae tractatus"),
    ("prdl-24370_de-purissima-et-immaculata-conceptione-virginis", "De conceptione B.M.V. (large)"),
    ("prdl-24369_de-purissima-et-immaculata-conceptione-virginis", "De conceptione B.M.V. (small)"),
]

PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$", re.M)
LATIN_PAGE_RE = re.compile(r"^---\s*Page\s+0*(\d+)\s*---\s*$\n(.*?)(?=^---\s*Page|\Z)", re.M | re.S)


def split_by_page(text: str) -> dict[int, str]:
    """Map page_num -> body of that page (between markers)."""
    result = {}
    matches = list(PAGE_RE.finditer(text))
    for i, m in enumerate(matches):
        pn = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[pn] = text[start:end].strip()
    return result


def main() -> int:
    out_dir = CORPUS / "_dual_grades" / "side_by_side"
    out_dir.mkdir(parents=True, exist_ok=True)

    for work_id, label in PRD:
        # Read the Latin OCR
        ocr_path = CORPUS / work_id / "translations" / "_reocr" / "qwen3vl-4b-trithemius-q6" / "full.txt"
        latin_by_page = split_by_page(ocr_path.read_text(encoding="utf-8", errors="replace")) if ocr_path.is_file() else {}
        # Codex
        codex_text = ""
        cdir = CORPUS / work_id / "translations" / CODEX / "full"
        if cdir.is_dir():
            for f in sorted(cdir.glob("full_chunk_*.md")):
                codex_text += f.read_text(encoding="utf-8", errors="replace") + "\n"
        codex_by_page = split_by_page(codex_text)
        # Qwen
        qwen_text = ""
        qdir = CORPUS / work_id / "translations" / QWEN / "full"
        if qdir.is_dir():
            for f in sorted(qdir.glob("full_chunk_*.md")):
                qwen_text += f.read_text(encoding="utf-8", errors="replace") + "\n"
        qwen_by_page = split_by_page(qwen_text)

        # Build side-by-side
        all_pages = sorted(set(latin_by_page) | set(codex_by_page) | set(qwen_by_page))
        md = [f"# {label} — `{work_id}`", ""]
        md.append(f"Latin OCR pages: {len(latin_by_page)} | Codex chunks covered: {len(codex_by_page)} | Qwen chunks covered: {len(qwen_by_page)}")
        md.append("")
        for pn in all_pages:
            latin = latin_by_page.get(pn, "(no OCR)")
            codex = codex_by_page.get(pn, "(no codex translation)")
            qwen = qwen_by_page.get(pn, "(no qwen translation)")
            md.append(f"## Page {pn:03d}")
            md.append("")
            md.append("**Latin (OCR witness):**")
            md.append("```")
            md.append(latin[:600] + ("…" if len(latin) > 600 else ""))
            md.append("```")
            md.append("")
            md.append("**Codex (gpt-5.5):**")
            md.append("```")
            md.append(codex[:1200] + ("…" if len(codex) > 1200 else ""))
            md.append("```")
            md.append("")
            md.append("**Qwen-4B-Trithemius:**")
            md.append("```")
            md.append(qwen[:1200] + ("…" if len(qwen) > 1200 else ""))
            md.append("```")
            md.append("")
            md.append("---")
            md.append("")

        out_path = out_dir / f"{work_id}_side_by_side.md"
        out_path.write_text("\n".join(md), encoding="utf-8")
        print(f"Wrote {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
