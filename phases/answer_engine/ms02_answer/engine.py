"""
Phase 3 answer engine orchestrator.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from ms02_corpus.p1_1_registry.registry import load_registry
from ms02_index.p2_4_retrieval.retriever import Retriever

from ms02_answer.gate import Route, classify_query
from ms02_answer.groq_client import groq_generate_answer, groq_should_run
from ms02_answer.generator import (
    build_factual_answer,
    detect_fact_intent,
    has_sufficient_grounding,
    pick_citation_url,
)
from ms02_answer.models import AnswerResult
from ms02_answer.templates import (
    INSUFFICIENT_CONTEXT,
    REFUSAL_ADVISORY,
    REFUSAL_OUT_OF_SCOPE,
    REFUSAL_PII,
)
from ms02_answer.validator import validate_result


class AnswerEngineError(RuntimeError):
    """Configuration or pipeline failure."""


class AnswerEngine:
    def __init__(
        self,
        *,
        vector_store_root: Path | None = None,
        normalized_root: Path | None = None,
        allowlist_path: Path | None = None,
        top_k: int = 5,
        use_groq: bool | None = None,
    ) -> None:
        phases = Path(__file__).resolve().parents[2]
        self.normalized_root = normalized_root or (phases / "corpus" / "normalized")
        self.allowlist_path = allowlist_path or (phases / "foundations" / "allowlist.yaml")
        self.registry = load_registry(self.allowlist_path)
        self._scheme_names = tuple(s.scheme_name for s in self.registry.schemes)
        self.retriever = Retriever(
            vector_store_root=vector_store_root,
            allowlist_path=self.allowlist_path,
        )
        self.top_k = top_k
        self._use_groq = use_groq if use_groq is not None else groq_should_run()

    def _last_updated_from_hits(self, scheme_ids: list[str]) -> str | None:
        dates: list[str] = []
        for sid in scheme_ids:
            man = self.normalized_root / sid / "manifest.json"
            if man.is_file():
                data = json.loads(man.read_text(encoding="utf-8"))
                raw = data.get("raw_fetched_at")
                if isinstance(raw, str) and raw.strip():
                    dates.append(raw.strip())
        if not dates:
            return None
        return max(dates)

    def _refusal_result(self, question: str, route: Route, answer: str) -> AnswerResult:
        return AnswerResult(
            question=question,
            answer=answer,
            source_url=None,
            last_updated=None,
            route=route.value,
            detail=None,
        )

    def ask(self, question: str) -> AnswerResult:
        route = classify_query(question, known_scheme_names=self._scheme_names)

        if route == Route.REFUSAL_PII:
            return self._refusal_result(question, route, REFUSAL_PII)
        if route == Route.REFUSAL_ADVISORY:
            return self._refusal_result(question, route, REFUSAL_ADVISORY)
        if route == Route.REFUSAL_OUT_OF_SCOPE:
            return self._refusal_result(question, route, REFUSAL_OUT_OF_SCOPE)
        if route == Route.INSUFFICIENT:
            return self._refusal_result(question, route, INSUFFICIENT_CONTEXT)

        hits = self.retriever.hybrid_search(question, top_k=self.top_k)

        if not hits:
            return self._refusal_result(question, Route.INSUFFICIENT, INSUFFICIENT_CONTEXT)

        answer_text = ""
        if self._use_groq:
            # RAG primary path: retrieved chunks → Groq prompt (Phase 3 design).
            answer_text = (
                groq_generate_answer(
                    question,
                    hits,
                    fact_intent=detect_fact_intent(question),
                )
                or ""
            )
            if not answer_text.strip():
                answer_text = build_factual_answer(question, hits)
        else:
            if not has_sufficient_grounding(question, hits):
                return self._refusal_result(
                    question, Route.INSUFFICIENT, INSUFFICIENT_CONTEXT
                )
            answer_text = build_factual_answer(question, hits)

        if not answer_text.strip():
            return self._refusal_result(question, Route.INSUFFICIENT, INSUFFICIENT_CONTEXT)

        source_url = pick_citation_url(hits)
        if not source_url or source_url not in self.registry.url_set():
            return self._refusal_result(question, Route.INSUFFICIENT, INSUFFICIENT_CONTEXT)

        scheme_ids = list(dict.fromkeys(h.scheme_id for h in hits[:3]))
        last_updated = self._last_updated_from_hits(scheme_ids)
        if last_updated and "T" in last_updated:
            last_updated = last_updated.split("T")[0]

        result = AnswerResult(
            question=question,
            answer=answer_text,
            source_url=source_url,
            last_updated=last_updated,
            route=Route.FACTUAL.value,
        )

        ok, err = validate_result(result, allowed_urls=self.registry.url_set())
        if not ok:
            return self._refusal_result(
                question,
                Route.INSUFFICIENT,
                INSUFFICIENT_CONTEXT,
            )

        return result


def _default_red_team_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "foundations"
        / "red-team-queries.yaml"
    )


def run_red_team_evaluation(engine: AnswerEngine | None = None) -> dict[str, Any]:
    import yaml

    engine = engine or AnswerEngine(use_groq=False)
    path = _default_red_team_path()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    queries = list(data.get("queries") or [])

    results: list[dict[str, Any]] = []
    for item in queries:
        q = str(item["text"])
        expected = str(item.get("expected_route", "factual"))
        res = engine.ask(q)
        has_url = bool(res.source_url)
        ok = False
        if expected == "factual":
            ok = res.route == Route.FACTUAL.value and has_url
        elif expected == "refusal":
            ok = res.route.startswith("refusal") and not has_url
        elif expected == "borderline":
            # Borderline: accept refusal without URL, or grounded factual with URL
            ok = (
                res.route.startswith("refusal")
                or res.route == Route.INSUFFICIENT.value
                or (res.route == Route.FACTUAL.value and has_url)
            ) and not (
                res.route.startswith("refusal") and has_url
            )
        elif expected == "insufficient":
            ok = res.route == Route.INSUFFICIENT.value and not has_url
        results.append(
            {
                "id": item.get("id"),
                "expected_route": expected,
                "actual_route": res.route,
                "has_url": has_url,
                "ok": ok,
            }
        )

    n = len(results)
    passed = sum(1 for r in results if r["ok"])
    return {
        "ok": passed == n,
        "passed": passed,
        "total": n,
        "results": results,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Phase 3 — answer engine.")
    p.add_argument("question", nargs="*", help="Question to answer.")
    p.add_argument("--red-team", action="store_true", help="Run red-team query eval.")
    p.add_argument(
        "--no-groq",
        action="store_true",
        help="Disable Groq LLM condensation (extractive-only, even if GROQ_API_KEY is set).",
    )
    p.add_argument("--json", action="store_true", help="JSON output only.")
    args = p.parse_args(list(argv) if argv is not None else None)

    if args.red_team or not args.question:
        report = run_red_team_evaluation(AnswerEngine(use_groq=False))
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report.get("ok") else 1

    question = " ".join(args.question)
    engine = AnswerEngine(use_groq=False if args.no_groq else None)
    result = engine.ask(question)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(result.display_text())
        print()
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
