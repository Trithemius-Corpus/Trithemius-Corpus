"""Check each dated AI assessment against its full scan and exact crop."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops

from edition_corrections import recorded_ledgers


def read_image(root: Path, record: dict, key: str) -> Path:
    path = (root / record[key]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Evidence image is outside the repository")
    if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError(f"Evidence image digest mismatch: {record[key]}")
    return path


def load(root: Path, work_id: str, *, as_of: str | None = None) -> dict:
    ledgers = recorded_ledgers(root, work_id, "scans")
    if not ledgers:
        return {}
    folder = root / "data/translation_disagreements" / work_id / "facsimiles"
    images = json.loads((folder / "images.json").read_text(encoding="utf-8"))
    crops = json.loads((folder / "crops.json").read_text(encoding="utf-8"))
    assessments = {}
    dates = {}
    for ledger in ledgers:
        if as_of and ledger["date"] > as_of:
            continue
        for key, item in ledger["items"].items():
            if item.get("supersedes_date") != dates.get(key):
                raise ValueError(f"{key}: scan revision does not identify its predecessor")
            if item["reviewer"] != "Codex AI" or item["human_review"] != "none_documented":
                raise ValueError(f"{key}: invalid scan-review attribution")
            img, crop = item["image"], item["crop"]
            if img != images[str(crop["canvas_number"])] or crops[key] != crop:
                raise ValueError(f"{key}: scan assessment differs from its image register")
            original_path = read_image(root, img, "path")
            crop_path = read_image(root, crop, "crop_path")
            x, y, width, height = crop["xywh"]
            with Image.open(original_path) as original, Image.open(crop_path) as pixels:
                if not (0 <= x < x + width <= original.width and 0 <= y < y + height <= original.height):
                    raise ValueError(f"{key}: crop bounds exceed original image")
                expected = original.crop((x, y, x + width, y + height)).convert("RGB")
                if pixels.size != expected.size or ImageChops.difference(expected, pixels.convert("RGB")).getbbox():
                    raise ValueError(f"{key}: crop differs from the declared source region")
            dates[key] = ledger["date"]
            assessments[key] = item
    return assessments
