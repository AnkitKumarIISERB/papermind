"""Embedding service using sentence-transformers (CPU-only, ~80MB model)."""

import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model once and cache it.
    all-MiniLM-L6-v2: 384-dim, ~80MB, <100ms per embedding on CPU.
    """
    logger.info(f"Loading embedding model: {settings.embedding_model_name}")
    model = SentenceTransformer(
        settings.embedding_model_name,
        device="cpu",
    )
    logger.info("Embedding model loaded successfully.")
    return model


def embed_text(text: str) -> list[float]:
    """
    Generate a 384-dimensional embedding for a single text string.

    Args:
        text: Input text (paper abstract, search query, etc.)

    Returns:
        List of floats representing the embedding vector.
    """
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
    return embedding.tolist()


def embed_texts_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Batch-embed multiple texts efficiently.
    Uses sentence-transformers' internal batching for optimal throughput.

    Args:
        texts: List of text strings to embed.
        batch_size: Number of texts per internal batch.

    Returns:
        List of embedding vectors (each is a list of 384 floats).
    """
    if not texts:
        return []

    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=batch_size,
    )
    return embeddings.tolist()
