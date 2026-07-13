"""Build per-cluster sentence-embedding retrieval indices for v2 translation.

For each cluster file in `data/anchors/<cluster>.jsonl`:
  - validate every pair has explicit `public_domain: true` on both sides
  - encode the Latin side with sentence-transformers
  - write `{sentences.jsonl, embeddings.npy, meta.json}` to
    `data/retrieval/<cluster>/`

The PD-affirmation check is the technical enforcement of the v2 licensing
policy (METHODOLOGY.md §5.2). The script will refuse to index any pair where
either `latin_source.public_domain` or `english_source.public_domain` is
missing or false.

Usage:
    python scripts/build_retrieval_index.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
ANCHORS_DIR = ROOT / "data" / "anchors"
OUT_DIR = ROOT / "data" / "retrieval"

# Multilingual MiniLM works well on Latin via Romance-language subword overlap;
# 384-dim embeddings; ~118 MB model download on first use.
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


class PDAffirmationError(RuntimeError):
    """Raised when a pair lacks an explicit public_domain affirmation."""


def validate_pair(pair: dict, src: str, line_no: int) -> None:
    """Raise PDAffirmationError unless both sides affirm public_domain."""
    pid = pair.get("id", "(no id)")
    for side in ("latin_source", "english_source"):
        block = pair.get(side, {})
        if block.get("public_domain") is not True:
            raise PDAffirmationError(
                f"REFUSED {src}:{line_no} id={pid} -- "
                f"{side}.public_domain is missing or not True"
            )
    if not pair.get("latin", "").strip() or not pair.get("english", "").strip():
        raise PDAffirmationError(
            f"REFUSED {src}:{line_no} id={pid} -- empty latin or english"
        )


def load_cluster_pairs(cluster_file: Path) -> list[dict]:
    cluster_id = cluster_file.stem
    out: list[dict] = []
    for i, line in enumerate(cluster_file.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            pair = json.loads(line)
        except json.JSONDecodeError as e:
            raise PDAffirmationError(f"{cluster_file.name}:{i} -- invalid JSON: {e}")
        validate_pair(pair, cluster_file.name, i)
        out.append({
            "id": pair["id"],
            "cluster": cluster_id,
            "ref": f"{pair.get('work', '')}, {pair.get('section', '')}",
            "latin": pair["latin"],
            "english": pair["english"],
            "latin_source": pair.get("latin_source", {}),
            "english_source": pair.get("english_source", {}),
        })
    return out


def build_cluster_index(cluster_file: Path, model: SentenceTransformer) -> int:
    """Build one cluster's index. Returns the number of pairs indexed."""
    cluster_id = cluster_file.stem
    out_dir = OUT_DIR / cluster_id
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = load_cluster_pairs(cluster_file)
    if not pairs:
        print(f"  [{cluster_id}] no pairs, skipping")
        return 0

    embs = model.encode(
        [p["latin"] for p in pairs],
        batch_size=64,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    np.save(out_dir / "embeddings.npy", embs.astype(np.float32))
    with (out_dir / "sentences.jsonl").open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    (out_dir / "meta.json").write_text(
        json.dumps({
            "cluster": cluster_id,
            "model": MODEL_NAME,
            "dim": int(embs.shape[1]),
            "count": int(embs.shape[0]),
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_file": cluster_file.name,
        }, indent=2),
        encoding="utf-8",
    )
    return len(pairs)


def main() -> int:
    if not ANCHORS_DIR.is_dir():
        print(f"ERROR: {ANCHORS_DIR} not found", file=sys.stderr)
        return 1
    cluster_files = sorted(ANCHORS_DIR.glob("*.jsonl"))
    if not cluster_files:
        print(f"ERROR: no .jsonl files in {ANCHORS_DIR}", file=sys.stderr)
        return 1

    print(f"clusters to index: {len(cluster_files)}")
    print(f"loading {MODEL_NAME}...")
    started = time.time()
    model = SentenceTransformer(MODEL_NAME)
    print(f"  model loaded in {time.time() - started:.1f}s")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    refused: list[tuple[str, str]] = []
    total = 0
    for cf in cluster_files:
        try:
            n = build_cluster_index(cf, model)
            total += n
            print(f"  [{cf.stem:25}] {n:>3} pairs indexed")
        except PDAffirmationError as e:
            print(f"  [{cf.stem:25}] REFUSED: {e}", file=sys.stderr)
            refused.append((cf.name, str(e)))

    if refused:
        print(f"\n{len(refused)} file(s) had refused pairs; aborting:", file=sys.stderr)
        for src, msg in refused:
            print(f"  {src}: {msg}", file=sys.stderr)
        return 2
    print(f"\nindexed {total} pairs across {len(cluster_files)} clusters at {OUT_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
