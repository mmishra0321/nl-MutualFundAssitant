"""Phase 2.2 — Embeddings."""

from ms02_index.p2_2_embeddings.embedder import (
    DEFAULT_MODEL_ID,
    EmbeddingError,
    embed_all,
    embedding_input_text,
    main,
    should_skip_chunk,
)

__all__ = [
    "DEFAULT_MODEL_ID",
    "EmbeddingError",
    "embed_all",
    "embedding_input_text",
    "main",
    "should_skip_chunk",
]
