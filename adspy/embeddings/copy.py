"""Copy embeddings via BGE-large (open weights, runs locally).

The model loads on first call and is cached in-process. 1024-dim vectors.
First load downloads ~1.3 GB from HuggingFace.
"""
from __future__ import annotations

from functools import lru_cache

from adspy.utils.logging import get_logger

log = get_logger(__name__)

MODEL_NAME = "BAAI/bge-large-en-v1.5"
DIM = 1024


@lru_cache(maxsize=1)
def _model():  # type: ignore[no-untyped-def]
    from sentence_transformers import SentenceTransformer

    log.info("copy_embedding_model_loading", model=MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


def embed_copy(text: str) -> list[float]:
    if not text or not text.strip():
        return [0.0] * DIM
    vec = _model().encode(text, normalize_embeddings=True)
    return [float(x) for x in vec]
