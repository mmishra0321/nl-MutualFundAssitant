"""Phase 2.1 — Markdown-aware chunking."""

from ms02_index.p2_1_chunking.chunker import (
    DOC_TYPE,
    ChunkRecord,
    ChunkingError,
    chunk_all,
    chunk_scheme,
    chunk_text,
    main,
)

__all__ = [
    "DOC_TYPE",
    "ChunkRecord",
    "ChunkingError",
    "chunk_all",
    "chunk_scheme",
    "chunk_text",
    "main",
]
