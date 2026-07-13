"""Cluster-aware retrieval for in-context Latin/English few-shot examples.

For each input Latin chunk during translation, returns the top-*k* nearest
parallel pairs from the cluster-matched retrieval index. Indices are loaded
lazily and cached per process.

Public API:

    from retrieve_examples import retrieval_for_cluster

    ri = retrieval_for_cluster("monastic-reform")
    examples = ri.retrieve("query Latin text...", k=3)
    # [{"ref": "...", "latin": "...", "english": "...", "score": 0.83}, ...]

Or as a CLI for testing:

    echo "Lorem ipsum..." | python scripts/retrieve_examples.py monastic-reform
"""
from __future__ import annotations

import functools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RETR_DIR = ROOT / "data" / "retrieval"
RETR_DIR_NPU = ROOT / "data" / "retrieval_npu"


class RetrievalIndex:
    def __init__(self, cluster: str, sentences: list[dict],
                 embeddings: np.ndarray, model_name: str) -> None:
        self.cluster = cluster
        self.sentences = sentences
        self.embeddings = embeddings
        self.model_name = model_name
        self._encoder = None

    @classmethod
    def load(cls, cluster: str, index_dir: Path = RETR_DIR) -> "RetrievalIndex":
        d = index_dir / cluster
        if not d.is_dir():
            raise FileNotFoundError(
                f"no retrieval index for cluster '{cluster}' at {d}; "
                f"run `python scripts/build_retrieval_index.py` "
                f"(or build_retrieval_index_npu.py for the NPU-encoder index) first"
            )
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        sents = [
            json.loads(l)
            for l in (d / "sentences.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()
        ]
        embs = np.load(d / "embeddings.npy")
        return cls(cluster, sents, embs, meta["model"])

    def encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self.model_name)
        return self._encoder

    def _encode_query(self, text: str):
        """Dispatch to FLM's NPU embed-gemma if this index was built with
        build_retrieval_index_npu.py (model_name == "npu:<tag>"), else to
        the local sentence-transformers CPU encoder."""
        if self.model_name.startswith("npu:"):
            from npu_embed_client import embed_via_flm
            real_model = self.model_name.split("npu:", 1)[1]
            return embed_via_flm([text], model=real_model)[0]
        return self.encoder().encode(
            [text], convert_to_numpy=True, normalize_embeddings=True,
        )[0]

    def retrieve(self, query_latin: str, k: int = 3,
                 min_score: float = 0.40,
                 diversity_threshold: float = 0.75) -> list[dict]:
        """Top-*k* nearest pairs by cosine similarity, with diversity enforcement.

        Lever E: instead of pure top-k (which can yield 3 nearly-identical
        anchors), use maximal marginal relevance (MMR). Pick the top candidate;
        for each subsequent slot, pick the highest-scoring candidate whose
        cosine similarity to ALL already-selected examples is below
        diversity_threshold. Defaults to 0.75 — pairs more similar than that
        are treated as duplicates.

        Returns at most *k* pairs with query-score >= min_score, sorted by
        score descending.
        """
        q_emb = self._encode_query(query_latin)
        scores = self.embeddings @ q_emb
        n = len(scores)
        if n == 0:
            return []

        # Take a wider candidate pool so MMR has options.
        pool_n = min(max(5 * k, k + 4), n)
        pool_idx = np.argpartition(-scores, pool_n - 1)[:pool_n]
        # Sort within pool by score desc
        pool_idx = pool_idx[np.argsort(-scores[pool_idx])]

        selected_idx: list[int] = []
        for idx in pool_idx:
            idx = int(idx)
            sc = float(scores[idx])
            if sc < min_score:
                continue
            # Diversity check: cosine to each already-selected example
            if selected_idx:
                sims = self.embeddings[selected_idx] @ self.embeddings[idx]
                if float(sims.max()) >= diversity_threshold:
                    continue
            selected_idx.append(idx)
            if len(selected_idx) >= k:
                break

        out: list[dict] = []
        for idx in selected_idx:
            row = self.sentences[idx]
            out.append({
                "ref": row.get("ref", ""),
                "cluster": row.get("cluster", self.cluster),
                "latin": row.get("latin", ""),
                "english": row.get("english", ""),
                "score": round(float(scores[idx]), 3),
            })
        return out


@functools.lru_cache(maxsize=16)
def retrieval_for_cluster(cluster: str, use_npu: bool = False) -> RetrievalIndex:
    """Load and cache a cluster's retrieval index for this process.

    use_npu=True loads the embed-gemma/FLM-encoded index (data/retrieval_npu/,
    built by build_retrieval_index_npu.py) instead of the default CPU
    sentence-transformers index (data/retrieval/)."""
    return RetrievalIndex.load(cluster, index_dir=RETR_DIR_NPU if use_npu else RETR_DIR)


def cluster_of_work(work_id: str, manifest_path: Path = ROOT / "manifest.json") -> str | None:
    """Look up the cluster ID for a work from manifest.json. Returns None if
    the work has no cluster assigned (which would happen for skipped works)."""
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    for w in m.get("works", []):
        if w.get("id") == work_id:
            return w.get("genre_cluster")
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: retrieve_examples.py <cluster>  (reads query Latin from stdin)",
              file=sys.stderr)
        return 1
    cluster = sys.argv[1]
    text = sys.stdin.read().strip()
    if not text:
        print("ERROR: empty query on stdin", file=sys.stderr)
        return 1
    ri = retrieval_for_cluster(cluster)
    for ex in ri.retrieve(text, k=3):
        print(json.dumps(ex, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
