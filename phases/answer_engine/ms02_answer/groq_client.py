"""Groq LLM generation (Phase 3) — RAG: retrieved chunks + prompt, no free-form knowledge."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ms02_index.p2_4_retrieval.retriever import RetrievalHit

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
_CONTEXT_CAP = 10_000

_SYSTEM_PROMPT = """You are a mutual-fund FAQ assistant using retrieval-augmented generation (RAG).

You will receive:
1) a user QUESTION, and
2) CONTEXT blocks copied from official HDFC scheme pages (retrieved chunks).

Rules:
- Your answer MUST be grounded ONLY in the CONTEXT blocks. Treat them as the sole source of truth.
- If CONTEXT does not contain enough information, reply exactly: "I do not have enough information in the retrieved sources to answer that."
- Answer ONLY the specific fact requested (NAV, minimum SIP, expense ratio, exit load, benchmark,
  lock-in, or riskometer). Do NOT list unrelated facts from the same page.
- At most THREE short sentences; prefer ONE sentence. Plain text only.
- No investment advice (no \"should\", \"better\", \"recommend\", \"consider investing\").
- Do NOT invent numbers, dates, fund names, or benchmarks not present in CONTEXT.
- Do NOT output URLs, links, http(s), or markdown links (citation is added separately)."""
MAX_CONTEXT_CHARS_PER_HIT = 2_800


def _build_context_block(hits: list[RetrievalHit]) -> str:
    """Format top-k retrieval hits for the LLM user message (RAG context)."""
    parts: list[str] = []
    for i, hit in enumerate(hits[:5], start=1):
        block = (
            f"### Retrieved chunk {i}\n"
            f"Scheme: {hit.scheme_name}\n"
            f"Section: {hit.section_heading}\n"
            f"Source page: {hit.source_url}\n"
            f"Content:\n{hit.text.strip()}"
        ).strip()
        if len(block) > MAX_CONTEXT_CHARS_PER_HIT:
            block = block[:MAX_CONTEXT_CHARS_PER_HIT] + "\n..."
        parts.append(block)
    return "\n\n".join(parts)


_DOTENV_LOADED = False


def _load_repo_dotenv() -> None:
    """Load repo-root `.env` if present (never overrides existing env vars)."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parents[3]
    load_dotenv(root / ".env", override=False)


def groq_should_run() -> bool:
    """Use Groq when API key present and MS02_USE_GROQ is not explicitly disabled."""
    _load_repo_dotenv()
    if not os.environ.get("GROQ_API_KEY", "").strip():
        return False
    flag = os.environ.get("MS02_USE_GROQ", "1").strip().lower()
    return flag not in {"0", "false", "no", "off"}


_INTENT_LABELS = {
    "nav": "NAV (net asset value) only",
    "minimum_sip": "minimum SIP amount only",
    "expense_ratio": "expense ratio only",
    "exit_load": "exit load only",
    "benchmark": "benchmark index only",
    "lock_in": "lock-in period only",
    "riskometer": "riskometer / risk classification only",
}


def groq_generate_answer(
    question: str,
    hits: list[RetrievalHit],
    *,
    model_id: str | None = None,
    fact_intent: str | None = None,
) -> str | None:
    """
    RAG answer from retrieved chunks + Groq chat prompt.
    Returns answer body (no citation URL), or None if API unavailable / error.
    """
    _load_repo_dotenv()
    try:
        from groq import Groq
    except ImportError:
        return None

    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return None

    model = (
        model_id
        or os.environ.get("GROQ_MODEL", "").strip()
        or DEFAULT_GROQ_MODEL
    )
    ctx = _build_context_block(hits)
    ctx = ctx[:_CONTEXT_CAP]

    intent_line = ""
    if fact_intent and fact_intent in _INTENT_LABELS:
        intent_line = (
            f"\nFocus: {_INTENT_LABELS[fact_intent]}. "
            "Ignore other numbers on the page that were not asked for.\n"
        )

    if not ctx.strip():
        return None

    client = Groq(api_key=key)
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.1,
            max_tokens=300,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Use ONLY the retrieved CONTEXT below to answer the QUESTION.\n\n"
                        f"QUESTION:\n{question.strip()}"
                        f"{intent_line}\n\n"
                        f"RETRIEVED CONTEXT (chunks from allowlisted scheme pages):\n{ctx}"
                    ),
                },
            ],
        )
    except Exception:
        return None

    choice = resp.choices[0] if resp.choices else None
    raw = choice.message.content if choice and choice.message else None
    if not raw or not str(raw).strip():
        return None

    cleaned = strip_urls_and_links(str(raw).strip())
    # Hard cap paragraphs to three sentences-ish
    if not cleaned:
        return None
    return cleaned


def strip_urls_and_links(text: str) -> str:
    """Remove URLs / markdown links (citation attached separately)."""
    text = re.sub(r"https?://[^\s\]>)]+", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def groq_condense_answer(
    question: str,
    hits: list[RetrievalHit],
    *,
    model_id: str | None = None,
    fact_intent: str | None = None,
) -> str | None:
    """Alias for :func:`groq_generate_answer` (backward compatible)."""
    return groq_generate_answer(
        question, hits, model_id=model_id, fact_intent=fact_intent
    )
