"""
Phase 2.4 — Retrieval (phased-architecture.md).

Top-k vector search over Chroma plus BM25 hybrid; optional scheme_id filter.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ms02_corpus.p1_1_registry.registry import Registry, load_registry
from ms02_index.p2_2_embeddings.embedder import DEFAULT_MODEL_ID, load_sentence_transformer
from ms02_index.p2_3_vector_store.loader import (
    COLLECTION_NAME,
    get_collection,
    get_persistent_client,
)
from ms02_index.p2_4_retrieval.keyword_boost import apply_keyword_boost
from ms02_index.p2_4_retrieval.scheme_resolver import resolve_scheme_id

DEFAULT_TOP_K = 5
DEFAULT_MODE = "hybrid"
RRF_K = 60
VECTOR_POOL_MULTIPLIER = 3


class RetrievalError(RuntimeError):
    """Index missing or search failure."""


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    scheme_id: str
    scheme_name: str
    source_url: str
    section_heading: str
    text: str
    score: float
    vector_score: float | None = None
    bm25_score: float | None = None
    rank: int = 0


def _default_vector_store_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "vector_store"


def _default_allowlist_path() -> Path:
    return Path(__file__).resolve().parents[3] / "foundations" / "allowlist.yaml"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9₹]+", text.lower())


class _BM25Index:
    def __init__(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        from rank_bm25 import BM25Okapi

        self.ids = ids
        self.documents = documents
        self.metadatas = metadatas
        self._corpus_tokens = [_tokenize(d) for d in documents]
        self._bm25 = BM25Okapi(self._corpus_tokens)

    def search(
        self,
        query: str,
        *,
        top_k: int,
        scheme_id: str | None = None,
    ) -> list[tuple[str, float]]:
        scores = np.asarray(self._bm25.get_scores(_tokenize(query)), dtype=np.float64)
        if scheme_id:
            for i, meta in enumerate(self.metadatas):
                if meta.get("scheme_id") != scheme_id:
                    scores[i] = -1.0
        if scores.size == 0 or scores.max() <= 0:
            return []
        order = np.argsort(scores)[::-1]
        out: list[tuple[str, float]] = []
        for idx in order:
            if scores[idx] <= 0:
                break
            out.append((self.ids[idx], float(scores[idx])))
            if len(out) >= top_k:
                break
        return out


def _load_store_manifest(vector_store_root: Path) -> dict[str, Any]:
    path = vector_store_root / "manifest.json"
    if not path.is_file():
        raise RetrievalError(f"Missing vector store manifest: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not manifest.get("ok"):
        raise RetrievalError(f"Vector store not ok: {manifest.get('error')}")
    return manifest


def _chroma_where(
    scheme_id: str | None = None,
    source_url: str | None = None,
) -> dict[str, str] | None:
    clauses: list[dict[str, str]] = []
    if scheme_id:
        clauses.append({"scheme_id": scheme_id})
    if source_url:
        clauses.append({"source_url": source_url})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _distance_to_similarity(distance: float) -> float:
    return max(0.0, 1.0 - float(distance))


def _rrf_fuse(rankings: list[list[str]], *, k: int = RRF_K) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


class Retriever:
    """Hybrid retriever over Phase 2.3 Chroma index."""

    def __init__(
        self,
        *,
        vector_store_root: Path | None = None,
        allowlist_path: Path | None = None,
        model_id: str | None = None,
    ) -> None:
        self.vector_store_root = vector_store_root or _default_vector_store_dir()
        self.allowlist_path = allowlist_path or _default_allowlist_path()
        self.registry = load_registry(self.allowlist_path)
        self._allowed_urls = self.registry.url_set()

        manifest = _load_store_manifest(self.vector_store_root)
        self.embedding_model_id = model_id or manifest.get(
            "embedding_model_id", DEFAULT_MODEL_ID
        )
        # Always open Chroma under vector_store_root (portable on Streamlit Cloud).
        chroma_dir = self.vector_store_root / "chroma"
        if not chroma_dir.is_dir():
            legacy = Path(str(manifest.get("persist_path", "")))
            if legacy.is_dir():
                chroma_dir = legacy
            else:
                raise RetrievalError(
                    f"Chroma directory missing: {chroma_dir} "
                    f"(legacy persist_path not found: {manifest.get('persist_path')})"
                )
        client = get_persistent_client(chroma_dir)
        self.collection = get_collection(
            client, name=manifest.get("collection_name", COLLECTION_NAME)
        )
        self._model = None
        self._bm25: _BM25Index | None = None

    @property
    def model(self):
        if self._model is None:
            self._model = load_sentence_transformer(self.embedding_model_id)
        return self._model

    @property
    def bm25(self) -> _BM25Index:
        if self._bm25 is None:
            data = self.collection.get(include=["documents", "metadatas"])
            ids = data.get("ids") or []
            if not ids:
                raise RetrievalError("Chroma collection is empty")
            self._bm25 = _BM25Index(
                ids=ids,
                documents=list(data.get("documents") or []),
                metadatas=list(data.get("metadatas") or []),
            )
        return self._bm25

    def _encode_query(self, query: str) -> list[float]:
        vec = self.model.encode(
            [query],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return np.asarray(vec[0], dtype=np.float32).tolist()

    def _meta_by_id(self) -> dict[str, dict[str, Any]]:
        data = self.collection.get(include=["metadatas", "documents"])
        return {
            cid: {
                **(meta or {}),
                "text": (doc or ""),
            }
            for cid, meta, doc in zip(
                data.get("ids") or [],
                data.get("metadatas") or [],
                data.get("documents") or [],
            )
        }

    def vector_search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        scheme_id: str | None = None,
        source_url: str | None = None,
    ) -> list[RetrievalHit]:
        if scheme_id is None:
            scheme_id = resolve_scheme_id(query, self.registry)
        if source_url and source_url not in self._allowed_urls:
            return []
        pool = max(top_k, top_k * VECTOR_POOL_MULTIPLIER)
        result = self.collection.query(
            query_embeddings=[self._encode_query(query)],
            n_results=min(pool, self.collection.count()),
            where=_chroma_where(scheme_id, source_url),
            include=["documents", "metadatas", "distances"],
        )
        return self._hits_from_chroma(result, top_k=top_k, mode="vector")

    def bm25_search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        scheme_id: str | None = None,
        source_url: str | None = None,
    ) -> list[RetrievalHit]:
        if scheme_id is None:
            scheme_id = resolve_scheme_id(query, self.registry)
        ranked = self.bm25.search(query, top_k=top_k * 2, scheme_id=scheme_id)
        meta_by_id = self._meta_by_id()
        hits: list[RetrievalHit] = []
        max_score = ranked[0][1] if ranked else 1.0
        for rank, (chunk_id, raw_score) in enumerate(ranked):
            meta = meta_by_id.get(chunk_id, {})
            hits.append(
                self._hit_from_meta(
                    chunk_id,
                    meta,
                    score=raw_score / max_score if max_score else raw_score,
                    bm25_score=raw_score,
                    rank=rank + 1,
                )
            )
        if source_url:
            hits = [h for h in hits if h.source_url == source_url]
        return self._validate_hits(hits[:top_k])

    def hybrid_search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        scheme_id: str | None = None,
        source_url: str | None = None,
    ) -> list[RetrievalHit]:
        if scheme_id is None:
            scheme_id = resolve_scheme_id(query, self.registry)
        if source_url and source_url not in self._allowed_urls:
            return []

        vec_hits = self.vector_search(
            query, top_k=top_k * 2, scheme_id=scheme_id, source_url=source_url
        )
        bm25_hits = self.bm25_search(
            query, top_k=top_k * 2, scheme_id=scheme_id, source_url=source_url
        )

        vec_ranking = [h.chunk_id for h in vec_hits]
        bm25_ranking = [h.chunk_id for h in bm25_hits]
        fused = _rrf_fuse([vec_ranking, bm25_ranking])

        vec_scores = {h.chunk_id: h.score for h in vec_hits}
        bm25_scores = {h.chunk_id: h.score for h in bm25_hits}
        meta_by_id = self._meta_by_id()

        ordered_pairs = apply_keyword_boost(
            sorted(fused.items(), key=lambda x: x[1], reverse=True),
            query=query,
            meta_by_id=meta_by_id,
        )[:top_k]
        ordered = ordered_pairs
        hits: list[RetrievalHit] = []
        for rank, (chunk_id, fused_score) in enumerate(ordered):
            meta = meta_by_id.get(chunk_id, {})
            hits.append(
                self._hit_from_meta(
                    chunk_id,
                    meta,
                    score=fused_score,
                    vector_score=vec_scores.get(chunk_id),
                    bm25_score=bm25_scores.get(chunk_id),
                    rank=rank + 1,
                )
            )
        return self._validate_hits(hits)

    def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        scheme_id: str | None = None,
        source_url: str | None = None,
        mode: str = DEFAULT_MODE,
    ) -> list[RetrievalHit]:
        if mode == "vector":
            return self.vector_search(
                query, top_k=top_k, scheme_id=scheme_id, source_url=source_url
            )
        if mode == "bm25":
            return self.bm25_search(
                query, top_k=top_k, scheme_id=scheme_id, source_url=source_url
            )
        return self.hybrid_search(
            query, top_k=top_k, scheme_id=scheme_id, source_url=source_url
        )

    def _hits_from_chroma(
        self, result: dict[str, Any], *, top_k: int, mode: str
    ) -> list[RetrievalHit]:
        ids = (result.get("ids") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        hits: list[RetrievalHit] = []
        for rank, (chunk_id, meta, doc, dist) in enumerate(
            zip(ids, metas, docs, dists)
        ):
            sim = _distance_to_similarity(dist)
            hits.append(
                self._hit_from_meta(
                    chunk_id,
                    {**(meta or {}), "text": doc or ""},
                    score=sim,
                    vector_score=sim if mode == "vector" else None,
                    rank=rank + 1,
                )
            )
            if len(hits) >= top_k:
                break
        return self._validate_hits(hits)

    def _hit_from_meta(
        self,
        chunk_id: str,
        meta: dict[str, Any],
        *,
        score: float,
        vector_score: float | None = None,
        bm25_score: float | None = None,
        rank: int = 0,
    ) -> RetrievalHit:
        return RetrievalHit(
            chunk_id=chunk_id,
            scheme_id=str(meta.get("scheme_id", "")),
            scheme_name=str(meta.get("scheme_name", "")),
            source_url=str(meta.get("source_url", "")),
            section_heading=str(meta.get("section_heading", "")),
            text=str(meta.get("text", "")),
            score=score,
            vector_score=vector_score,
            bm25_score=bm25_score,
            rank=rank,
        )

    def _validate_hits(self, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        valid: list[RetrievalHit] = []
        for h in hits:
            if h.source_url not in self._allowed_urls:
                continue
            if h.scheme_id not in {s.id for s in self.registry.schemes}:
                continue
            valid.append(h)
        return valid


def _default_golden_path() -> Path:
    return Path(__file__).resolve().parent / "golden_queries.yaml"


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Phase 2.4 — hybrid retrieval.")
    p.add_argument("query", nargs="*", help="Search query (omit for --golden).")
    p.add_argument("--golden", "-g", action="store_true", help="Run golden-query eval.")
    p.add_argument(
        "--mode",
        choices=("hybrid", "vector", "bm25"),
        default=DEFAULT_MODE,
        help="Retrieval mode (default: hybrid).",
    )
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Number of hits.")
    p.add_argument("--scheme-id", default=None, help="Force scheme_id metadata filter.")
    p.add_argument("--source-url", default=None, help="Force source_url metadata filter.")
    args = p.parse_args(list(argv) if argv is not None else None)

    if args.golden or not args.query:
        from ms02_index.p2_4_retrieval.eval import run_golden_evaluation

        report = run_golden_evaluation()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report.get("ok") else 1

    query = " ".join(args.query)
    retriever = Retriever()
    hits = retriever.search(
        query,
        top_k=args.top_k,
        scheme_id=args.scheme_id,
        source_url=args.source_url,
        mode=args.mode,
    )
    payload = {
        "query": query,
        "mode": args.mode,
        "resolved_scheme_id": resolve_scheme_id(query, retriever.registry),
        "scheme_id_filter": args.scheme_id,
        "source_url_filter": args.source_url,
        "hits": [asdict(h) for h in hits],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if hits else 1


if __name__ == "__main__":
    raise SystemExit(main())
