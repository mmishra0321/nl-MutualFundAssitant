"""End-to-end answer golden tests and red-team replay."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ms02_answer.engine import AnswerEngine, run_red_team_evaluation
from ms02_answer.gate import Route
from ms02_answer.validator import validate_result
from ms02_corpus.p1_1_registry.registry import Registry, load_registry
from ms02_index.p2_4_retrieval.eval import run_golden_evaluation


def _default_answer_golden_path() -> Path:
    return Path(__file__).resolve().parents[2] / "golden_tests" / "answer_golden.yaml"


def run_answer_golden_evaluation(
    engine: AnswerEngine,
    *,
    golden_path: Path | None = None,
    registry: Registry | None = None,
) -> dict[str, Any]:
    path = golden_path or _default_answer_golden_path()
    reg = registry or engine.registry
    allowed = reg.url_set()
    scheme_urls = {s.id: s.url for s in reg.schemes}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    items = list(data.get("queries") or [])

    results: list[dict[str, Any]] = []
    for item in items:
        q = str(item["text"])
        expected = str(item.get("expected_route", "factual"))
        res = engine.ask(q)
        valid, verr = validate_result(res, allowed_urls=allowed)
        ok = bool(valid)

        if ok and expected == "factual":
            sid = item.get("expected_scheme_id")
            if sid and res.source_url != scheme_urls.get(str(sid)):
                ok = False
                verr = f"expected citation for {sid}"
            tokens = [str(t).lower() for t in (item.get("answer_must_contain_any") or [])]
            if tokens and not any(t in res.answer.lower() for t in tokens):
                ok = False
                verr = f"missing any of: {tokens}"
        elif ok and expected == "refusal":
            ok = res.route.startswith("refusal") and not res.source_url
            if not ok:
                verr = "expected refusal without URL"
        elif ok and expected == "insufficient":
            ok = res.route == Route.INSUFFICIENT.value and not res.source_url
            if not ok:
                verr = "expected insufficient without URL"

        results.append(
            {
                "id": item.get("id"),
                "expected_route": expected,
                "actual_route": res.route,
                "has_url": bool(res.source_url),
                "validator_ok": valid,
                "ok": ok,
                "error": verr,
            }
        )

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    return {
        "ok": passed == total and total > 0,
        "passed": passed,
        "total": total,
        "results": results,
    }


def run_retrieval_golden(retriever=None) -> dict[str, Any]:
    return run_golden_evaluation(retriever=retriever)


def run_red_team(engine: AnswerEngine | None = None) -> dict[str, Any]:
    return run_red_team_evaluation(engine)
