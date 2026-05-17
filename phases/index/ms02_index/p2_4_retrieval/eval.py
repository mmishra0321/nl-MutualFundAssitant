"""
Golden-query evaluation for Phase 2.4 (hybrid vs vector-only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ms02_index.p2_4_retrieval.retriever import Retriever, RetrievalHit

DEFAULT_GOLDEN_PATH = Path(__file__).resolve().parent / "golden_queries.yaml"


def _first_rank_with_scheme(hits: list[RetrievalHit], scheme_id: str) -> int | None:
    for h in hits:
        if h.scheme_id == scheme_id:
            return h.rank
    return None


def _hits_match_content(hits: list[RetrievalHit], patterns: list[str]) -> bool:
    if not hits:
        return False
    for h in hits:
        blob = (h.text + " " + h.section_heading).lower()
        if any(p.lower() in blob for p in patterns):
            return True
    return False


def _mrr(rank: int | None) -> float:
    return 0.0 if rank is None else 1.0 / rank


def load_golden_queries(path: Path | None = None) -> list[dict[str, Any]]:
    golden_path = path or DEFAULT_GOLDEN_PATH
    data = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
    return list(data.get("queries") or [])


def evaluate_query(
    retriever: Retriever,
    item: dict[str, Any],
    *,
    top_k: int = 5,
) -> dict[str, Any]:
    query = str(item["query"])
    expected = str(item["expected_scheme_id"])
    must_any = list(item.get("must_match_any") or [])

    vec_hits = retriever.vector_search(query, top_k=top_k)
    hybrid_hits = retriever.hybrid_search(query, top_k=top_k)

    vec_rank = _first_rank_with_scheme(vec_hits, expected)
    hybrid_rank = _first_rank_with_scheme(hybrid_hits, expected)

    vec_top_ok = bool(vec_hits) and vec_hits[0].scheme_id == expected
    hybrid_top_ok = bool(hybrid_hits) and hybrid_hits[0].scheme_id == expected

    vec_url_ok = bool(vec_hits) and vec_hits[0].source_url in retriever.registry.url_set()
    hybrid_url_ok = bool(hybrid_hits) and hybrid_hits[0].source_url in retriever.registry.url_set()

    content_ok = _hits_match_content(hybrid_hits, must_any) if must_any else True

    vec_mrr = _mrr(vec_rank)
    hybrid_mrr = _mrr(hybrid_rank)

    return {
        "id": item.get("id"),
        "query": query,
        "expected_scheme_id": expected,
        "vector_top1_scheme_ok": vec_top_ok,
        "hybrid_top1_scheme_ok": hybrid_top_ok,
        "vector_allowlist_ok": vec_url_ok,
        "hybrid_allowlist_ok": hybrid_url_ok,
        "hybrid_content_ok": content_ok,
        "vector_mrr": vec_mrr,
        "hybrid_mrr": hybrid_mrr,
        "hybrid_beats_vector": hybrid_mrr >= vec_mrr,
        "hybrid_strictly_better": hybrid_mrr > vec_mrr,
        "vector_top_chunk_id": vec_hits[0].chunk_id if vec_hits else None,
        "hybrid_top_chunk_id": hybrid_hits[0].chunk_id if hybrid_hits else None,
        "ok": hybrid_top_ok and hybrid_url_ok and content_ok,
    }


def run_golden_evaluation(
    *,
    golden_path: Path | None = None,
    retriever: Retriever | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    retriever = retriever or Retriever()
    queries = load_golden_queries(golden_path)
    per_query = [evaluate_query(retriever, q, top_k=top_k) for q in queries]

    n = len(per_query)
    hybrid_top1 = sum(1 for r in per_query if r["hybrid_top1_scheme_ok"])
    vector_top1 = sum(1 for r in per_query if r["vector_top1_scheme_ok"])
    hybrid_mrr_sum = sum(r["hybrid_mrr"] for r in per_query)
    vector_mrr_sum = sum(r["vector_mrr"] for r in per_query)
    hybrid_beats = sum(1 for r in per_query if r["hybrid_beats_vector"])
    hybrid_strict = sum(1 for r in per_query if r["hybrid_strictly_better"])
    all_ok = sum(1 for r in per_query if r["ok"])

    return {
        "ok": all_ok == n and hybrid_mrr_sum >= vector_mrr_sum,
        "total_queries": n,
        "hybrid_top1_accuracy": hybrid_top1 / n if n else 0.0,
        "vector_top1_accuracy": vector_top1 / n if n else 0.0,
        "hybrid_mean_reciprocal_rank": hybrid_mrr_sum / n if n else 0.0,
        "vector_mean_reciprocal_rank": vector_mrr_sum / n if n else 0.0,
        "hybrid_beats_or_ties_vector_count": hybrid_beats,
        "hybrid_strictly_better_count": hybrid_strict,
        "queries_passing": all_ok,
        "results": per_query,
    }


def main() -> int:
    report = run_golden_evaluation()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
