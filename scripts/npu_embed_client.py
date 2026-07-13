"""Minimal HTTP client for FLM's /v1/embeddings endpoint (NPU-resident
embed-gemma:300m), used as an alternative to sentence-transformers so the
retrieval encoder can run on the NPU alongside the Qwen translation model
instead of on CPU.

Requires the FLM server to be started with --embed 1 (co-loads the embed
sidecar in the SAME process as the primary chat model -- this is the
pattern documented in NPURUNBOOK.HTML section 2). Does NOT start or
restart the server; that is an operational decision made by the caller.

Usage:
    from npu_embed_client import embed_via_flm
    vecs = embed_via_flm(["Ait illi Iesus...", "Ego sum via..."])
    # vecs: np.ndarray [N, 768], L2-normalized (cosine == dot product)
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import numpy as np

DEFAULT_URL = "http://127.0.0.1:52625"
DEFAULT_MODEL = "embed-gemma:300m"


class FlmEmbeddingsUnavailable(RuntimeError):
    """Raised when the /v1/embeddings endpoint doesn't respond as expected --
    most commonly because the server wasn't started with --embed 1."""


def embed_via_flm(texts: list[str], model: str = DEFAULT_MODEL,
                   base_url: str = DEFAULT_URL, timeout: int = 30) -> np.ndarray:
    """POST texts to FLM's OpenAI-compatible /v1/embeddings endpoint.

    Returns L2-normalized float32 [len(texts), dim] so downstream cosine
    similarity is a plain dot product, matching build_retrieval_index.py's
    convention (normalize_embeddings=True there too).
    """
    payload = {"model": model, "input": texts}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise FlmEmbeddingsUnavailable(
            f"FLM /v1/embeddings unreachable at {base_url} -- is the server "
            f"running with --embed 1? ({type(exc).__name__}: {exc})"
        ) from exc
    if "data" not in data:
        raise FlmEmbeddingsUnavailable(
            f"unexpected /v1/embeddings response (no 'data' key, embed "
            f"sidecar likely not loaded): {str(data)[:300]}"
        )
    rows = sorted(data["data"], key=lambda r: r.get("index", 0))
    vecs = np.array([r["embedding"] for r in rows], dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def check_available(model: str = DEFAULT_MODEL, base_url: str = DEFAULT_URL) -> bool:
    """Cheap probe: True if the embed sidecar is up, False otherwise (never
    raises). Use before batch work to fail fast with a clear message."""
    try:
        embed_via_flm(["probe"], model=model, base_url=base_url, timeout=8)
        return True
    except FlmEmbeddingsUnavailable:
        return False


if __name__ == "__main__":
    import sys
    ok = check_available()
    print(f"FLM /v1/embeddings ({DEFAULT_MODEL} @ {DEFAULT_URL}): "
          f"{'AVAILABLE' if ok else 'NOT AVAILABLE -- start FLM with --embed 1'}")
    sys.exit(0 if ok else 1)
