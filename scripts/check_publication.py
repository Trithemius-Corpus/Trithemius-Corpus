"""Validate the committed publication in place. This entry point only reads it."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    "validate_release", "validate_reader", "validate_passages", "validate_iiif",
    "validate_study_reader", "validate_cipher_trace", "validate_witness_comparison",
    "validate_editorial_copy", "validate_publication_exports", "validate_translation_disagreements",
    "validate_scribes_followup", "validate_edition_contracts", "validate_reader_tools",
)


def main() -> None:
    for name in CHECKS:
        print(f"Checking {name}", flush=True)
        subprocess.run([sys.executable, "-B", "-X", "utf8", str(ROOT / "scripts" / f"{name}.py")],
                       cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
