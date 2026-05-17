"""
Validate Phase 3 output contract.
"""

from __future__ import annotations

import re

from ms02_answer.gate import Route
from ms02_answer.models import AnswerResult

MAX_SENTENCES = 3


def _count_sentences(text: str) -> int:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return len([p for p in parts if p.strip()])


def validate_result(
    result: AnswerResult,
    *,
    allowed_urls: frozenset[str],
) -> tuple[bool, str | None]:
    routes_without_url = {
        Route.REFUSAL_ADVISORY.value,
        Route.REFUSAL_PII.value,
        Route.REFUSAL_OUT_OF_SCOPE.value,
        Route.INSUFFICIENT.value,
    }

    if result.route in routes_without_url:
        if result.source_url:
            return False, f"{result.route} must not include source_url"
        if result.last_updated:
            return False, f"{result.route} must not include last_updated"
        return True, None

    if result.route == Route.FACTUAL.value:
        if not result.source_url:
            return False, "factual route requires source_url"
        if result.source_url not in allowed_urls:
            return False, "source_url not in allowlist"
        if _count_sentences(result.answer) > MAX_SENTENCES:
            return False, f"answer exceeds {MAX_SENTENCES} sentences"
        if not result.last_updated:
            return False, "factual route requires last_updated"
        return True, None

    return False, f"unknown route: {result.route}"
