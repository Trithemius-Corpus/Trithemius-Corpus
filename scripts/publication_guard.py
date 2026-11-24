"""Stage publication updates and preserve the meaning of published passage IDs."""
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "data" / "publication"


@lru_cache(maxsize=8)
def read_input(name: str):
    return json.loads((INPUTS / name).read_text(encoding="utf-8"))


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def passages(path: Path) -> dict[str, str]:
    records = json.loads(path.read_text(encoding="utf-8"))["passages"]
    result = {r["html_id"]: digest(r["text"]) for r in records}
    if len(result) != len(records):
        raise ValueError(f"Duplicate passage IDs in {path.name}")
    return result


def fingerprint(rows: dict[str, str]) -> str:
    return digest(json.dumps(rows, sort_keys=True, separators=(",", ":")))


def rendered_passages(page: Path) -> dict[str, str]:
    from lxml import html
    from passage_model import plain_text
    document = html.fromstring(page.read_text(encoding="utf-8"))
    elements = document.xpath("//*[@data-passage-id]")
    rows = {e.get("data-passage-id"): digest(plain_text(html.tostring(e, encoding="unicode", with_tail=False)))
            for e in elements}
    if len(rows) != len(elements):
        raise ValueError(f"{page.name}: duplicate rendered passage IDs")
    return rows


def undo_migrations(rows: dict[str, str], changes: list[dict], page: str) -> dict[str, str]:
    """Apply the exact inverse of approved edits to compare with the baseline."""
    original = dict(rows)
    for change in reversed(changes):
        key, before, after = change["id"], change["before"], change["after"]
        if not change["reason"].strip() or original.get(key) != after:
            raise ValueError(f"Migration does not match the rendered text at {key}")
        if after is None:
            replacement = change.get("replacement_id")
            if replacement not in rows or f'id="{key}"' not in page:
                raise ValueError(f"Missing redirect for retired passage {key}")
        if before is None:
            original.pop(key)
        else:
            original[key] = before
    return original


def validate_tree(dist: Path, previous: Path | None = None) -> None:
    contract = read_input("passage-contract.json")
    migrations = read_input("passage-migrations.json")
    indexes = {p.stem: p for p in (dist / "data/passages").glob("*.json")}
    if indexes.keys() != contract["works"].keys():
        raise ValueError("Published work inventory differs from the passage contract")
    for work, path in indexes.items():
        current = passages(path)
        changes = [m for m in migrations if m["work"] == work]
        expected = contract["works"][work]
        page = dist / "works" / f"{work}.html"
        if rendered_passages(page) != current:
            raise ValueError(f"{work}: visible reading text disagrees with its passage index")
        baseline = undo_migrations(current, changes, page.read_text(encoding="utf-8") if changes else "")
        if len(baseline) != expected["count"] or fingerprint(baseline) != expected["sha256"]:
            raise ValueError(f"{work}: passage IDs or their text changed without a recorded migration")
        if previous:
            old_path = previous / "data/passages" / path.name
            if old_path.is_file():
                old = passages(old_path)
                for key in old.keys() | current.keys():
                    if old.get(key) != current.get(key) and not any(
                        m["id"] == key and m["before"] == old.get(key) for m in changes
                    ):
                        raise ValueError(f"{work}#{key}: existing passage changed without a migration")
    for work, config in contract["apparatus"].items():
        reading = (dist / "works" / f"{work}.html").read_text(encoding="utf-8")
        for key in config["types"]:
            filename = f"{work}_style-c-{key}.html"
            if filename not in reading or not (dist / "works" / filename).is_file():
                raise ValueError(f"Missing or unlinked {key} apparatus for {work}")


@contextmanager
def staged_directory(target: Path, *, seed: bool, lock_target: Path | None = None):
    """Serialize writers. Keep the old tree recoverable across a failed rename."""
    if target.is_symlink():
        raise ValueError(f"Cannot replace a symlinked publication directory: {target}")
    target = target.resolve()
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    lock_dir = Path(tempfile.gettempdir()) / "trithemius-publication-locks"
    lock_dir.mkdir(exist_ok=True)
    lock_key = os.path.normcase(str((lock_target or target).resolve()))
    lock = lock_dir / (digest(lock_key) + ".lock")
    previous = parent / f".{target.name}-previous"
    marker = parent / f".{target.name}-swap"
    with lock.open("a+b") as handle:
        if not handle.tell():
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if previous.is_symlink() or marker.is_symlink():
            raise ValueError(f"Unsafe publication recovery path for {target}")
        if marker.exists() and marker.read_text(encoding="utf-8") != str(target):
            raise ValueError(f"Unrecognized publication recovery marker: {marker}")
        if previous.exists():
            if not marker.is_file():
                raise ValueError(f"Unrecognized backup at {previous}")
            if target.exists():
                shutil.rmtree(previous)
            else:
                previous.rename(target)
        marker.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(prefix=".edition-build-", dir=parent) as scratch:
            stage = Path(scratch) / target.name
            if seed and target.is_dir():
                shutil.copytree(target, stage)
            else:
                stage.mkdir()
            yield stage
            if target.is_dir():
                marker.write_text(str(target), encoding="utf-8")
                target.rename(previous)
            try:
                stage.rename(target)
            except BaseException:
                if previous.exists() and not target.exists():
                    previous.rename(target)
                marker.unlink(missing_ok=True)
                raise
            if previous.exists():
                shutil.rmtree(previous)
            marker.unlink(missing_ok=True)
