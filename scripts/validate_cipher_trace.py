#!/usr/bin/env python3
"""Release checks for the executable cipher edition."""
import csv
import json
from lxml import html as html_parser

from build_cipher_trace import ROOT, load_and_compute


def main() -> None:
    data = load_and_compute()
    statuses = {data["facsimile"]["evidence_status"], data["cover"]["status"], data["cipher_stream"]["status"], data["extraction"]["status"], data["decode"]["status"], data["intentio"]["status"]}
    required = {"printed-evidence", "transcription-repair", "inferred-operation"}
    assert required <= statuses, "edition must distinguish evidence, repair, and inference"
    assert data["passage"]["precision"] in {"passage", "segment"}
    assert data["computed"]["cover_sample_initials"] == "gafzgbc"
    assert data["computed"]["decoded"].startswith("ichbi")
    page = ROOT / "site" / "dist" / "cipher-solutions.html"
    html = page.read_text(encoding="utf-8")
    for needle in ("trace-step", "aria-current", "Download JSON", "Download TSV", "Plain-text account", "Where the print disagrees"):
        assert needle in html, f"cipher page lacks {needle!r}"
    downloads = ROOT / "site/dist/data/cipher-traces"
    assert json.loads((downloads / "modus-ii.json").read_text(encoding="utf-8")) == data, "stale JSON trace"
    with (downloads / "modus-ii.tsv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert rows == [
        {"position": str(row["position"]), "cipher": row["cipher"], "decoded": row["decoded"],
         "evidence_status": "inferred-operation"} for row in data["computed"]["rows"]
    ], "stale TSV trace"
    table = html_parser.fromstring(html).xpath("//table[caption='Complete Modus II substitution table']")[0]
    plains = table.xpath("thead/tr/th[position() > 1]/text()")
    ciphers = table.xpath("tbody/tr/td/text()")
    assert [a + b for a, b in zip(plains, ciphers, strict=True)] == data["printed_substitution_pairs"]
    comparison = html_parser.fromstring(html).xpath("//table[caption='Printed line, intended German and cover words by position']/tbody/tr")
    expected = [[str(row["position"]), *(row[key] or "—" for key in
                 ("printed", "decoded", "intended", "required_cipher", "cover_word", "cover_initial"))]
                for row in data["computed"]["comparison"]]
    assert [[cell.text_content() for cell in row] for row in comparison] == expected
    assert data["passage"]["parallel_href"] in html
    for key in ("crop", "page", "rule_page"):
        target = data["facsimile"][key]
        assert target in html and (ROOT / "site/dist" / target).is_file(), target
    print(f"cipher trace validation passed: {data['id']}")


if __name__ == "__main__":
    main()
