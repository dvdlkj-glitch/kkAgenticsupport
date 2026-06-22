"""Embedding generation. Default backend is local sentence-transformers (free).

Switch to OpenAI embeddings by setting EMBEDDING_BACKEND=openai in .env.
Keep EMBEDDING_DIM and the vector(...) size in schema.sql in sync with the model.
"""
from __future__ import annotations

from functools import lru_cache

from .config import settings


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model_local)


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI

    key = settings.openai_api_key
    if not key:
        raise RuntimeError("EMBEDDING_BACKEND=openai but OPENAI_API_KEY is not set.")
    return OpenAI(api_key=key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return one embedding vector per input text."""
    if not texts:
        return []

    if settings.embedding_backend == "openai":
        resp = _openai_client().embeddings.create(
            model=settings.embedding_model_openai, input=texts
        )
        return [d.embedding for d in resp.data]

    # local (default)
    model = _local_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_one(text: str) -> list[float]:
    return embed_texts([text])[0]
