"""Run the pinned official EPUBCheck distribution without vendoring its JAR."""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


VERSION = "5.3.0"
URL = f"https://github.com/w3c/epubcheck/releases/download/v{VERSION}/epubcheck-{VERSION}.zip"
SHA256 = "6c07e68584b2e2ce2f89fe06e1246dfead3eb36b46b340e7d93524f29dcff6c5"


def executable(cache: Path) -> list[str]:
    jar = cache / f"epubcheck-{VERSION}" / "epubcheck.jar"
    if not jar.exists():
        cache.mkdir(parents=True, exist_ok=True)
        archive = cache / f"epubcheck-{VERSION}.zip"
        if not archive.exists():
            urllib.request.urlretrieve(URL, archive)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != SHA256:
            archive.unlink(missing_ok=True)
            raise RuntimeError(f"EPUBCheck archive checksum mismatch: {digest}")
        with zipfile.ZipFile(archive) as package:
            package.extractall(cache)
    return ["java", "-jar", str(jar)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", nargs="+")
    args = parser.parse_args()
    cache = Path(os.environ.get("EPUBCHECK_CACHE", Path(tempfile.gettempdir()) / "trithemius-epubcheck"))
    command = executable(cache)
    failed = False
    for epub in args.epub:
        proc = subprocess.run([*command, epub], check=False)
        failed |= proc.returncode != 0
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
