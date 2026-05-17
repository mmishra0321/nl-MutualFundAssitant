"""Problem-statement success criteria — aggregate gate for Phase 5 handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def evaluate_success_criteria(
    *,
    step_results: dict[str, bool],
    repo_root: Path,
) -> dict[str, Any]:
    """
    Map architecture / problem-statement success criteria to pipeline steps.

    ``step_results`` keys match pipeline step names (e.g. ``retrieval_golden``).
    """
    criteria: list[dict[str, Any]] = [
        {
            "id": "SC-01",
            "label": "Accurate retrieval of factual mutual fund information",
            "ok": step_results.get("retrieval_golden", False)
            and step_results.get("corpus_spot_check", False),
        },
        {
            "id": "SC-02",
            "label": "Strict adherence to facts-only responses (red-team refusals)",
            "ok": step_results.get("red_team", False),
        },
        {
            "id": "SC-03",
            "label": "Valid single source citations on factual answers",
            "ok": step_results.get("answer_golden", False)
            and step_results.get("citation_urls", False),
        },
        {
            "id": "SC-04",
            "label": "Proper refusal of advisory / PII / out-of-scope queries",
            "ok": step_results.get("red_team", False)
            and step_results.get("answer_golden", False),
        },
        {
            "id": "SC-05",
            "label": "Clean minimal UI with visible disclaimer",
            "ok": step_results.get("streamlit_disclaimer", False)
            and step_results.get("disclaimer_artifacts", False),
        },
        {
            "id": "SC-06",
            "label": "README deliverable (setup, schemes, RAG, limitations)",
            "ok": step_results.get("root_readme", False),
        },
        {
            "id": "SC-07",
            "label": "Security: log sanitization + API ignores PII fields",
            "ok": step_results.get("log_sanitization", False)
            and step_results.get("api_security", False),
        },
        {
            "id": "SC-08",
            "label": "Ops: scheduled refresh workflow present",
            "ok": (repo_root / ".github/workflows/refresh-corpus-index.yml").is_file(),
        },
    ]
    passed = sum(1 for c in criteria if c["ok"])
    return {
        "ok": passed == len(criteria),
        "passed": passed,
        "total": len(criteria),
        "criteria": criteria,
    }
