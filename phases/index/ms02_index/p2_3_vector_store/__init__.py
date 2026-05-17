"""Phase 2.3 — Vector store (Chroma)."""

from ms02_index.p2_3_vector_store.loader import (
    BACKEND,
    COLLECTION_NAME,
    VectorStoreError,
    build_vector_store,
    chroma_metadata,
    get_collection,
    get_persistent_client,
    load_into_chroma,
    main,
    validate_chunk_row,
)

__all__ = [
    "BACKEND",
    "COLLECTION_NAME",
    "VectorStoreError",
    "build_vector_store",
    "chroma_metadata",
    "get_collection",
    "get_persistent_client",
    "load_into_chroma",
    "main",
    "validate_chunk_row",
]
