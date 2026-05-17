"""Phase 1.4 — Normalization to Markdown + provenance."""

from ms02_corpus.p1_4_normalization.normalizer import (
    DOC_TYPE,
    NormalizeManifest,
    html_fragment_to_markdown,
    main,
    normalize_all,
    normalize_scheme,
)

__all__ = [
    "DOC_TYPE",
    "NormalizeManifest",
    "html_fragment_to_markdown",
    "main",
    "normalize_all",
    "normalize_scheme",
]
