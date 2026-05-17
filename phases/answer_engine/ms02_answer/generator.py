"""
Grounded answer generation from retrieved chunks (extractive, no hallucination).

Answers one fact type per query (expense ratio, SIP, NAV, exit load, benchmark,
lock-in, riskometer) per problemstatement.md.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from ms02_index.p2_4_retrieval.retriever import RetrievalHit

# Fact intents aligned with problemstatement.md §2 FAQ examples.
FACT_EXIT_LOAD = "exit_load"
FACT_EXPENSE_RATIO = "expense_ratio"
FACT_MINIMUM_SIP = "minimum_sip"
FACT_NAV = "nav"
FACT_BENCHMARK = "benchmark"
FACT_LOCK_IN = "lock_in"
FACT_RISKOMETER = "riskometer"

_GENERIC_QUERY_TERMS = frozenset(
    {
        "fund",
        "funds",
        "scheme",
        "schemes",
        "mutual",
        "the",
        "what",
        "how",
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
        "this",
        "that",
        "tell",
        "about",
        "please",
        "much",
        "have",
        "does",
        "do",
    }
)

_SCHEME_ONLY_TERMS = frozenset(
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
    }
)


def detect_fact_intent(query: str) -> Optional[str]:
    """Return the primary fact type the user asked for, or None if ambiguous."""
    ql = query.lower().replace("-", " ")

    if "exit" in ql and "load" in ql:
        return FACT_EXIT_LOAD
    if "expense" in ql or ("ratio" in ql and "exit" not in ql):
        return FACT_EXPENSE_RATIO
    if "sip" in ql or "minimum" in ql:
        return FACT_MINIMUM_SIP
    if "benchmark" in ql:
        return FACT_BENCHMARK
    if "lock" in ql and ("in" in ql or "period" in ql):
        return FACT_LOCK_IN
    if "riskometer" in ql or ("risk" in ql and "classif" in ql):
        return FACT_RISKOMETER
    if re.search(r"\bnav\b", ql):
        return FACT_NAV
    if "aum" in ql or "fund size" in ql:
        return None  # not a primary problem-statement fact; avoid dumping NAV block
    return None


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9₹%]+", text.lower()) if len(t) > 2]


def _meaningful_query_terms(query: str) -> list[str]:
    return [t for t in _tokenize(query) if t not in _GENERIC_QUERY_TERMS]


def _query_is_scheme_name_only(query: str) -> bool:
    meaningful = _meaningful_query_terms(query)
    return bool(meaningful) and all(t in _SCHEME_ONLY_TERMS for t in meaningful)


def _is_boilerplate_sentence(sentence: str) -> bool:
    s = sentence.strip()
    if s.startswith("#"):
        return True
    if s.count("###") >= 2:
        return True
    if len(sentence) > 500:
        return True
    if sentence.count("](") >= 2:
        return True
    if "Show More" in sentence or "Calculator](/" in sentence:
        return True
    if sentence.count("/mutual-funds/") > 2:
        return True
    return False


def _extract_nav(blob: str) -> Optional[str]:
    m = re.search(
        r"Latest NAV as of\s+([^.\n]+?)\s+is\s+₹\s*([\d,]+(?:\.\d+)?)",
        blob,
        re.I,
    )
    if m:
        return f"The latest NAV as of {m.group(1).strip()} is ₹{m.group(2)}."
    m = re.search(
        r"NAV:\s*([^₹\n]{3,30}?)\s*₹\s*([\d,]+(?:\.\d+)?)",
        blob,
        re.I,
    )
    if m:
        when = m.group(1).strip().strip("'")
        return f"The NAV as of {when} is ₹{m.group(2)}."
    return None


def _extract_minimum_sip(blob: str) -> Optional[str]:
    m = re.search(r"Min\.?\s*for\s*SIP\s*₹\s*([\d,]+)", blob, re.I)
    if m:
        return f"The minimum SIP amount is ₹{m.group(1)}."
    m = re.search(
        r"Minimum SIP Investment is set to ₹\s*([\d,]+)",
        blob,
        re.I,
    )
    if m:
        return f"The minimum SIP amount is ₹{m.group(1)}."
    return None


def _extract_expense_ratio(blob: str) -> Optional[str]:
    m = re.search(r"Expense\s*ratio\s*([\d.]+\s*%)", blob, re.I)
    if m:
        return f"The expense ratio is {m.group(1).strip()}."
    return None


def _extract_exit_load(blob: str) -> Optional[str]:
    m = re.search(
        r"Exit load of\s+([^.\n]{5,120}\.)",
        blob,
        re.I,
    )
    if m:
        return f"Exit load: {m.group(1).strip()}"
    return None


def _extract_benchmark(blob: str) -> Optional[str]:
    m = re.search(
        r"Fund benchmark\s*([A-Z0-9][^\n\[\(]{4,120}?)(?:\[|\n|$)",
        blob,
        re.I,
    )
    if m:
        idx = m.group(1).strip()
        return f"The benchmark index is {idx}."
    m = re.search(
        r"benchmark\s*(?:index\s*)?(?:is\s*)?([A-Z][^\n\[\(]{4,100}?)(?:\[|\n|$)",
        blob,
        re.I,
    )
    if m:
        return f"The benchmark index is {m.group(1).strip()}."
    return None


def _extract_lock_in(blob: str) -> Optional[str]:
    m = re.search(
        r"lock[- ]?in\s*(?:period\s*)?(?:of\s*)?([^.\n]{5,120}\.)",
        blob,
        re.I,
    )
    if m:
        return f"Lock-in: {m.group(1).strip()}"
    m = re.search(r"(\d+)\s*year[s]?\s+lock[- ]?in", blob, re.I)
    if m:
        return f"The lock-in period is {m.group(1)} years."
    return None


def _extract_riskometer(blob: str) -> Optional[str]:
    m = re.search(
        r"is rated\s+([^.\n]+?)\s+risk",
        blob,
        re.I,
    )
    if m:
        label = m.group(1).strip()
        return f"The riskometer classification is {label} risk."
    m = re.search(r"riskometer[:\s]+([^.\n]{3,40})", blob, re.I)
    if m:
        return f"The riskometer classification is {m.group(1).strip()}."
    return None


_EXTRACTORS: dict[str, Callable[[str], Optional[str]]] = {
    FACT_NAV: _extract_nav,
    FACT_MINIMUM_SIP: _extract_minimum_sip,
    FACT_EXPENSE_RATIO: _extract_expense_ratio,
    FACT_EXIT_LOAD: _extract_exit_load,
    FACT_BENCHMARK: _extract_benchmark,
    FACT_LOCK_IN: _extract_lock_in,
    FACT_RISKOMETER: _extract_riskometer,
}


def _extract_intent_fact(blob: str, intent: str) -> Optional[str]:
    fn = _EXTRACTORS.get(intent)
    if not fn:
        return None
    return fn(blob)


def _blob_matches_scheme(query: str, blob: str) -> bool:
    meaningful = _meaningful_query_terms(query)
    if not meaningful:
        return True
    blob_l = blob.lower()
    return any(t in blob_l for t in meaningful)


def extract_grounded_sentences(
    query: str,
    hits: list[RetrievalHit],
    *,
    max_sentences: int = 3,
    intent: Optional[str] = None,
) -> list[str]:
    if not hits:
        return []

    fact_intent = intent or detect_fact_intent(query)

    if fact_intent:
        for hit in hits[:6]:
            blob = f"{hit.section_heading}\n{hit.text}"
            if not _blob_matches_scheme(query, blob):
                continue
            answer = _extract_intent_fact(blob, fact_intent)
            if answer and not _is_boilerplate_sentence(answer):
                return [answer]

    # Fallback: sentence scoring (still respect intent when set)
    q_terms = _tokenize(query)
    if not q_terms:
        return []

    seen: set[str] = set()
    scored: list[tuple[float, str]] = []
    for hit in hits[:4]:
        for sent in re.split(r"(?<=[.!?])\s+|\n+", f"{hit.section_heading}. {hit.text}"):
            s = re.sub(r"\s+", " ", sent.strip())
            if len(s) < 20 or _is_boilerplate_sentence(s):
                continue
            if fact_intent:
                sl = s.lower()
                intent_ok = {
                    FACT_NAV: "nav" in sl,
                    FACT_MINIMUM_SIP: "sip" in sl,
                    FACT_EXPENSE_RATIO: "expense" in sl,
                    FACT_EXIT_LOAD: "exit" in sl and "load" in sl,
                    FACT_BENCHMARK: "benchmark" in sl,
                    FACT_LOCK_IN: "lock" in sl,
                    FACT_RISKOMETER: "risk" in sl,
                }.get(fact_intent, True)
                if not intent_ok:
                    continue
            key = s[:80].lower()
            if key in seen:
                continue
            score = sum(1.0 for t in q_terms if t in s.lower())
            if score > 0.5:
                seen.add(key)
                scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:max_sentences]]


def has_sufficient_grounding(query: str, hits: list[RetrievalHit]) -> bool:
    if _query_is_scheme_name_only(query):
        return False
    if not hits:
        return False

    intent = detect_fact_intent(query)
    if intent:
        snippets = extract_grounded_sentences(query, hits, max_sentences=1, intent=intent)
        return bool(snippets)

    snippets = extract_grounded_sentences(query, hits, max_sentences=1)
    if not snippets or _is_boilerplate_sentence(snippets[0]):
        return False

    top = hits[0]
    blob = (top.text + " " + top.section_heading).lower()
    meaningful = _meaningful_query_terms(query)
    if meaningful:
        return any(t in blob for t in meaningful)

    ql = query.lower()
    fact_hooks = (
        "expense",
        "ratio",
        "sip",
        "exit",
        "load",
        "benchmark",
        "nav",
        "lock",
        "minimum",
        "riskometer",
    )
    return any(h in ql for h in fact_hooks)


def build_factual_answer(query: str, hits: list[RetrievalHit]) -> str:
    intent = detect_fact_intent(query)
    max_s = 1 if intent else 3
    sentences = extract_grounded_sentences(
        query, hits, max_sentences=max_s, intent=intent
    )
    if not sentences:
        return ""
    if intent:
        return sentences[0]
    return " ".join(sentences[:3])


def pick_citation_url(hits: list[RetrievalHit]) -> str | None:
    if not hits:
        return None
    return hits[0].source_url or None
