#!/usr/bin/env python3
"""Release checks for the executable cipher edition."""
from pathlib import Path

from build_cipher_trace import ROOT, load_and_compute


def main() -> None:
    data = load_and_compute()
    statuses = {data["facsimile"]["evidence_status"], data["cover"]["status"], data["cipher_stream"]["status"], data["extraction"]["status"], data["decode"]["status"], data["intentio"]["status"]}
    required = {"printed-evidence", "transcription-repair", "inferred-operation"}
    assert required <= statuses, "edition must distinguish evidence, repair, and inference"
    assert data["passage"]["precision"] in {"passage", "segment"}
    assert data["computed"]["cover_sample_initials"] == "gafzgqccg"
    page = ROOT / "site" / "dist" / "cipher-solutions.html"
    html = page.read_text(encoding="utf-8")
    for needle in ("trace-step", "aria-current", "Download JSON", "Download TSV", "Plain-text account", "No silent emendation"):
        assert needle in html, f"cipher page lacks {needle!r}"
    for artifact in ("modus-ii.json", "modus-ii.tsv"):
        assert (ROOT / "site" / "dist" / "data" / "cipher-traces" / artifact).exists()
    print(f"cipher trace validation passed: {data['id']}")


if __name__ == "__main__":
    main()
