#!/usr/bin/env python3
"""Validate and publish committed executable cipher-trace data."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "cipher_traces" / "modus-ii.json"
OUT = ROOT / "site" / "dist" / "data" / "cipher-traces"


def load_and_compute(path: Path = SOURCE) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    alphabet = data["alphabet"]
    pairs = data["printed_substitution_pairs"]
    if len(alphabet) != 24 or len(pairs) != 24:
        raise ValueError("Modus II requires a complete 24-letter alphabet")
    if "".join(pair[0] for pair in pairs) != alphabet:
        raise ValueError("pair plaintext column does not match the declared alphabet")
    inverse = {pair[1]: pair[0] for pair in pairs}
    if len(inverse) != 24:
        raise ValueError("cipher column is not one-to-one")
    extracted = "".join(re.findall(r"[a-z]", data["cipher_stream"]["transcription"].lower()))
    positions = data["cover"]["significant_positions"]
    cover_initials = "".join(data["cover"]["tokens"][position - 1][0].lower() for position in positions)
    decoded = "".join(inverse[letter] for letter in extracted)
    if extracted != data["extraction"]["result"]:
        raise ValueError("committed extraction result is not recomputable")
    if decoded != data["decode"]["result"]:
        raise ValueError("committed decode result is not recomputable")
    data["computed"] = {
        "extracted": extracted,
        "decoded": decoded,
        "cover_sample_initials": cover_initials,
        "mapping": [{"plain": p[0], "cipher": p[1]} for p in pairs],
        "rows": [
            {"position": index, "cipher": cipher, "decoded": plain}
            for index, (cipher, plain) in enumerate(zip(extracted, decoded), 1)
        ],
    }
    return data


def publish(data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "modus-ii.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (OUT / "modus-ii.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["position", "cipher", "decoded", "evidence_status"])
        for row in data["computed"]["rows"]:
            writer.writerow([row["position"], row["cipher"], row["decoded"], "inferred-operation"])


if __name__ == "__main__":
    trace = load_and_compute()
    publish(trace)
    print(f"cipher trace valid: {trace['id']} ({len(trace['computed']['decoded'])} letters)")
