"""
Lightweight post-fusion boost for factual MF queries (Phase 2.4 optional rerank).

Favors chunks whose heading/body contain query terms and common fund facts
(expense ratio, exit load, SIP, lock-in, benchmark) without a cross-encoder.
"""

from __future__ import annotations

import re
from typing import Any

# Terms that often appear in user factual queries on Groww scheme pages.
FACTUAL_TERMS: frozenset[str] = frozenset(
    {
        "expense",
        "ratio",
        "exit",
        "load",
        "sip",
        "lock",
        "benchmark",
        "minimum",
        "investment",
        "nav",
        "aum",
        "risk",
    }
)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9₹]+", text.lower())


def keyword_boost_score(query: str, meta: dict[str, Any]) -> float:
    """Additive boost in [0, ~0.5] based on term overlap with chunk text."""
    q_tokens = [t for t in _tokenize(query) if len(t) > 2]
    blob = (
        f"{meta.get('section_heading', '')} {meta.get('text', '')}"
    ).lower()
    if not blob.strip():
        return 0.0

    boost = 0.0
    matched_query = 0
    for tok in q_tokens:
        if tok in blob:
            matched_query += 1
            boost += 0.04
    if matched_query >= 2:
        boost += 0.05

    q_lower = query.lower()
    for term in FACTUAL_TERMS:
        if term in q_lower and term in blob:
            boost += 0.06

    return min(boost, 0.5)


def apply_keyword_boost(
    ordered: list[tuple[str, float]],
    *,
    query: str,
    meta_by_id: dict[str, dict[str, Any]],
) -> list[tuple[str, float]]:
    """Re-rank (chunk_id, base_score) pairs with keyword boost."""
    boosted = [
        (cid, score + keyword_boost_score(query, meta_by_id.get(cid, {})))
        for cid, score in ordered
    ]
    return sorted(boosted, key=lambda x: x[1], reverse=True)
