"""
Resolve optional scheme_id filter from natural-language queries.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms02_corpus.p1_1_registry.registry import Registry

# More specific patterns first.
_SCHEME_PATTERNS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("elss", "tax saver", "tax-saver"), "hdfc_elss_tax_saver_direct_growth"),
    (("mid cap", "mid-cap", "midcap"), "hdfc_mid_cap_direct_growth"),
    (("large cap", "large-cap", "largecap"), "hdfc_large_cap_direct_growth"),
    (("focused fund", "focused"), "hdfc_focused_direct_growth"),
    (("equity fund", "hdfc equity"), "hdfc_equity_direct_growth"),
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def resolve_scheme_id(query: str, registry: Registry | None = None) -> str | None:
    """
    Return scheme_id when the query names a fund; else None (search all five).
    """
    q = _normalize(query)

    for keywords, scheme_id in _SCHEME_PATTERNS:
        if any(kw in q for kw in keywords):
            return scheme_id

    if registry is None:
        return None

    for entry in registry.schemes:
        slug_words = entry.slug.replace("-", " ")
        if slug_words in q:
            return entry.id
        # e.g. "hdfc mid cap fund direct growth"
        name_norm = _normalize(entry.scheme_name)
        if len(name_norm) > 12 and name_norm in q:
            return entry.id
        # distinctive tokens: require "hdfc" + two scheme-specific tokens
        tokens = [t for t in re.split(r"[^a-z0-9]+", name_norm) if len(t) > 2]
        if "hdfc" in q and sum(1 for t in tokens if t in q) >= 2:
            return entry.id

    return None
