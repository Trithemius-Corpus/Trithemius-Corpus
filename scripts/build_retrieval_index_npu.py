"""Build per-cluster retrieval indices using the NPU-resident embed-gemma:300m
(via FLM's /v1/embeddings) instead of CPU sentence-transformers.

Mirrors build_retrieval_index.py exactly (same anchor source, same PD
licensing gate, same {sentences.jsonl, embeddings.npy, meta.json} layout)
so retrieve_examples.py can load either index by cluster name. Writes to a
SEPARATE directory (data/retrieval_npu/) so the existing CPU-MiniLM index
is untouched -- both can be compared side by side.

Requires FLM to be serving with --embed 1 (see npu_embed_client.py). Does
NOT start/restart FLM -- run npu_embed_client.py first to confirm the
embed sidecar is up before running this (it will refuse with a clear error
otherwise, cheaply, before touching any cluster).

Usage:
    python scripts/build_retrieval_index_npu.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ANCHORS_DIR = ROOT / "data" / "anchors"
OUT_DIR = ROOT / "data" / "retrieval_npu"
MODEL_NAME = "embed-gemma:300m"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_retrieval_index import load_cluster_pairs, PDAffirmationError  # noqa: E402
from npu_embed_client import embed_via_flm, check_available, FlmEmbeddingsUnavailable  # noqa: E402


def build_cluster_index(cluster_file: Path) -> int:
    cluster_id = cluster_file.stem
    out_dir = OUT_DIR / cluster_id
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = load_cluster_pairs(cluster_file)
    if not pairs:
        print(f"  [{cluster_id}] no pairs, skipping")
        return 0

    embs = embed_via_flm([p["latin"] for p in pairs], model=MODEL_NAME)
    np.save(out_dir / "embeddings.npy", embs.astype(np.float32))
    with (out_dir / "sentences.jsonl").open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    (out_dir / "meta.json").write_text(
        json.dumps({
            "cluster": cluster_id,
            "model": f"npu:{MODEL_NAME}",
            "dim": int(embs.shape[1]),
            "count": int(embs.shape[0]),
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_file": cluster_file.name,
        }, indent=2),
        encoding="utf-8",
    )
    return len(pairs)


def main() -> int:
    if not check_available(MODEL_NAME):
        print(f"ERROR: FLM /v1/embeddings not available for {MODEL_NAME}. "
              f"Start FLM with --embed 1 first (see npu_embed_client.py).",
              file=sys.stderr)
        return 1
    if not ANCHORS_DIR.is_dir():
        print(f"ERROR: {ANCHORS_DIR} not found", file=sys.stderr)
        return 1

    total = 0
    try:
        for cluster_file in sorted(ANCHORS_DIR.glob("*.jsonl")):
            n = build_cluster_index(cluster_file)
            print(f"  [{cluster_file.stem}] indexed {n} pairs -> {OUT_DIR / cluster_file.stem}")
            total += n
    except PDAffirmationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except FlmEmbeddingsUnavailable as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"\nTotal: {total} pairs indexed across "
          f"{len(list(ANCHORS_DIR.glob('*.jsonl')))} clusters -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
