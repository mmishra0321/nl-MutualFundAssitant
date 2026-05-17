"""
Query gate — route questions before retrieval / generation.
"""

from __future__ import annotations

import re
from enum import Enum

# PAN (simplified), email, 10-digit phone, 12-digit aadhaar-like groups
_PII_PATTERNS = (
    re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"),
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
)

_PII_KEYWORDS = (
    "pan number",
    "my pan",
    "aadhaar",
    "aadhar",
    "account number",
    "bank account",
    "otp",
    "one time password",
    "email address",
    "phone number",
    "mobile number",
    "folio number",
    "my folio",
)

_ADVISORY_PATTERNS = (
    re.compile(r"\bshould\s+i\s+(invest|buy|sell|switch)", re.I),
    re.compile(r"\bwhich\s+.*\bbetter\b", re.I),
    re.compile(r"\bwhich\s+(fund|scheme)\s+is\s+better\b", re.I),
    re.compile(r"\b(is it|is now)\s+a\s+good\s+time\s+to\b", re.I),
    re.compile(r"\brecommend\b", re.I),
    re.compile(r"\bhow much should i invest\b", re.I),
    re.compile(r"\bsell my\b.*\b(switch|buy)\b", re.I),
    re.compile(r"\bbetter\s*,\s*", re.I),
)

_OUT_OF_SCOPE_HINTS = (
    "small cap",
    "flexi cap",
    "hybrid fund",
    "debt fund",
    "amfi",
    "sebi website",
)

# Tokens that are not a specific fund/AMC name (overlap checks, unknown-fund detection).
_GENERIC_FUND_WORDS = frozenset(
    {
        "fund",
        "funds",
        "scheme",
        "schemes",
        "mutual",
        "mf",
        "direct",
        "growth",
        "plan",
        "what",
        "how",
        "much",
        "tell",
        "about",
        "the",
        "for",
        "is",
        "are",
        "of",
        "in",
        "on",
        "a",
        "an",
        "and",
        "or",
        "minimum",
        "min",
        "sip",
        "expense",
        "ratio",
        "exit",
        "load",
        "benchmark",
        "nav",
        "aum",
        "lock",
        "period",
        "riskometer",
        "groww",
        "page",
        "pages",
        "this",
        "that",
        "please",
        "show",
        "give",
    }
)

_FUND_NAME_RE = re.compile(
    r"\b([a-z][a-z0-9-]{2,})\s+(?:mutual\s+)?fund\b"
    r"|\b(?:mutual\s+)?fund\s+([a-z][a-z0-9-]{2,})\b",
    re.I,
)

# User must ask about a concrete fact — not only name a scheme (e.g. "hdfc mid cap").
_FACT_INTENT_PHRASES = (
    "expense",
    "ratio",
    "sip",
    "exit",
    "load",
    "benchmark",
    "nav",
    "lock-in",
    "lock in",
    "lockin",
    "minimum",
    "min sip",
    "riskometer",
    "aum",
    "fund size",
    "redemption",
    "statement",
    "download",
    "folio",
    "ter",
    "total expense",
)

_SCHEME_LABEL_TOKENS = frozenset(
    {
        "hdfc",
        "mid",
        "cap",
        "midcap",
        "large",
        "largecap",
        "equity",
        "focused",
        "elss",
        "tax",
        "saver",
        "direct",
        "growth",
        "plan",
        "fund",
        "funds",
        "scheme",
        "mutual",
    }
)


class Route(str, Enum):
    FACTUAL = "factual"
    REFUSAL_ADVISORY = "refusal_advisory"
    REFUSAL_PII = "refusal_pii"
    REFUSAL_OUT_OF_SCOPE = "refusal_out_of_scope"
    INSUFFICIENT = "insufficient"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def contains_pii(text: str) -> bool:
    q = text
    ql = _normalize(text)
    if any(p.search(q) for p in _PII_PATTERNS):
        return True
    return any(kw in ql for kw in _PII_KEYWORDS)


def is_advisory(text: str) -> bool:
    return any(p.search(text) for p in _ADVISORY_PATTERNS)


def has_factual_intent(text: str) -> bool:
    """True when the user asks for a specific fact, not only a fund name."""
    ql = _normalize(text)
    return any(phrase in ql for phrase in _FACT_INTENT_PHRASES)


def is_scheme_only_query(text: str, *, known_scheme_names: tuple[str, ...]) -> bool:
    """
    True when the message names an in-corpus scheme but does not ask a factual question.
    Example: "hdfc mid cap" → True; "exit load for hdfc mid cap" → False.
    """
    if has_factual_intent(text):
        return False
    ql = _normalize(text)
    if not _references_known_scheme(ql, known_scheme_names):
        return False
    extra = [
        w
        for w in re.findall(r"[a-z0-9]+", ql)
        if w not in _SCHEME_LABEL_TOKENS and w not in _GENERIC_FUND_WORDS
    ]
    return len(extra) == 0


def _known_fund_tokens(known_scheme_names: tuple[str, ...]) -> frozenset[str]:
    tokens = set(_GENERIC_FUND_WORDS)
    tokens.update(
        {
            "hdfc",
            "mid",
            "cap",
            "large",
            "equity",
            "focused",
            "elss",
            "tax",
            "saver",
            "midcap",
            "largecap",
        }
    )
    for name in known_scheme_names:
        for tok in re.findall(r"[a-z0-9]+", _normalize(name)):
            if len(tok) > 2:
                tokens.add(tok)
    return frozenset(tokens)


def _references_known_scheme(ql: str, known_scheme_names: tuple[str, ...]) -> bool:
    """True when the question clearly targets one of the five allowlisted HDFC schemes."""
    if "hdfc" not in ql:
        return False
    for name in known_scheme_names:
        nn = _normalize(name)
        if nn in ql:
            return True
        if any(tok in ql for tok in _normalize(name).split() if len(tok) > 4):
            return True
    if any(
        kw in ql
        for kw in (
            "mid cap",
            "mid-cap",
            "large cap",
            "large-cap",
            "equity fund",
            "focused",
            "elss",
            "tax saver",
            "tax-saver",
        )
    ):
        return True
    known = _known_fund_tokens(known_scheme_names)
    hits = [t for t in re.findall(r"[a-z0-9]+", ql) if t in known and t not in _GENERIC_FUND_WORDS]
    return len(hits) >= 2


def mentions_unknown_fund_name(text: str, *, known_scheme_names: tuple[str, ...]) -> bool:
    """
    True when the user names a fund/scheme that is not in the five-scheme corpus.
    """
    ql = _normalize(text)
    if _references_known_scheme(ql, known_scheme_names):
        return False

    known = _known_fund_tokens(known_scheme_names)

    for m in _FUND_NAME_RE.finditer(ql):
        candidate = (m.group(1) or m.group(2) or "").lower()
        if candidate and candidate not in known:
            return True

    if "fund" in ql or "scheme" in ql:
        for word in re.findall(r"[a-z0-9]+", ql):
            if len(word) < 4:
                continue
            if word in known or word in _GENERIC_FUND_WORDS:
                continue
            return True

    return False


def is_likely_out_of_scope(text: str, *, known_scheme_names: tuple[str, ...]) -> bool:
    ql = _normalize(text)
    if mentions_unknown_fund_name(text, known_scheme_names=known_scheme_names):
        return True
    if any(h in ql for h in _OUT_OF_SCOPE_HINTS):
        return True
    if "hdfc" in ql:
        # Named one of our five schemes → in scope for factual attempt
        for name in known_scheme_names:
            if _normalize(name) in ql or any(
                tok in ql for tok in _normalize(name).split() if len(tok) > 4
            ):
                return False
        # HDFC but not a listed scheme name
        if not any(
            kw in ql
            for kw in (
                "mid cap",
                "large cap",
                "equity fund",
                "focused",
                "elss",
                "tax saver",
            )
        ):
            return True
    return False


def classify_query(
    question: str,
    *,
    known_scheme_names: tuple[str, ...] = (),
) -> Route:
    if contains_pii(question):
        return Route.REFUSAL_PII
    if is_advisory(question):
        return Route.REFUSAL_ADVISORY
    if is_likely_out_of_scope(question, known_scheme_names=known_scheme_names):
        return Route.REFUSAL_OUT_OF_SCOPE
    if is_scheme_only_query(question, known_scheme_names=known_scheme_names):
        return Route.INSUFFICIENT
    return Route.FACTUAL
