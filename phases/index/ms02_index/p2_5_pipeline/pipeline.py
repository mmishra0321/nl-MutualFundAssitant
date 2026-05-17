"""
Phase 2.5 — Full index job (phased-architecture.md).

Runs 2.1 chunking → 2.2 embeddings → 2.3 vector store → 2.4 golden retrieval
checks from current Phase 1 normalized/ output.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ms02_corpus.p1_1_registry.registry import Registry, load_registry
from ms02_index.p2_1_chunking.chunker import ChunkingError, chunk_all
from ms02_index.p2_2_embeddings.embedder import DEFAULT_MODEL_ID, EmbeddingError, embed_all
from ms02_index.p2_3_vector_store.loader import VectorStoreError, build_vector_store
from ms02_index.p2_4_retrieval.eval import run_golden_evaluation
from ms02_index.p2_4_retrieval.retriever import RetrievalError, Retriever

EXPECTED_SCHEME_COUNT = 5


class PipelineError(RuntimeError):
    """A pipeline step failed."""


@dataclass
class StepResult:
    step: str
    ok: bool
    detail: dict[str, Any]


def _phases_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def _index_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_normalized_dir() -> Path:
    return _phases_dir() / "corpus" / "normalized"


def _default_chunks_dir() -> Path:
    return _index_dir() / "chunks"


def _default_embeddings_dir() -> Path:
    return _index_dir() / "embeddings"


def _default_vector_store_dir() -> Path:
    return _index_dir() / "vector_store"


def _default_allowlist_path() -> Path:
    return _phases_dir() / "foundations" / "allowlist.yaml"


def run_validate_allowlist_sh() -> str:
    script = _phases_dir() / "foundations" / "validate_allowlist.sh"
    if not script.is_file():
        raise PipelineError(f"Missing validate_allowlist.sh: {script}")
    proc = subprocess.run(
        ["bash", str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise PipelineError(err or out or f"validate_allowlist.sh exit {proc.returncode}")
    return out or "allowlist OK"


def run_unittests() -> None:
    root = _index_dir()
    corpus = _phases_dir() / "corpus"
    env = {**os.environ, "PYTHONPATH": f"{root}:{corpus}"}
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise PipelineError(proc.stderr or proc.stdout or "unittest failed")


def _preflight_normalized(registry: Registry, normalized_root: Path) -> None:
    missing: list[str] = []
    for entry in registry.schemes:
        page = normalized_root / entry.id / "page.md"
        if not page.is_file():
            missing.append(str(page))
    if missing:
        raise PipelineError(
            "normalized/ missing page.md for schemes (run Phase 1 first): "
            + "; ".join(missing)
        )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _validate_chunks_metadata(
    chunks_root: Path, registry: Registry
) -> tuple[bool, dict[str, Any]]:
    """Ensure every chunk has allowlisted source_url and valid scheme_id."""
    allowed_urls = registry.url_set()
    allowed_ids = {s.id for s in registry.schemes}
    errors: list[dict[str, str]] = []
    jsonl_files = sorted(
        p for p in chunks_root.glob("*.jsonl") if p.name != "skipped.jsonl"
    )
    if len(jsonl_files) != len(registry.schemes):
        errors.append(
            {
                "chunk_id": "",
                "reason": (
                    f"expected {len(registry.schemes)} scheme jsonl files, "
                    f"found {len(jsonl_files)}"
                ),
            }
        )
    total_chunks = 0
    for path in jsonl_files:
        rows = _read_jsonl(path)
        total_chunks += len(rows)
        for row in rows:
            cid = str(row.get("chunk_id", path.stem))
            url = (row.get("source_url") or "").strip()
            sid = (row.get("scheme_id") or "").strip()
            if sid not in allowed_ids:
                errors.append(
                    {"chunk_id": cid, "reason": f"invalid scheme_id: {sid!r}"}
                )
            elif url not in allowed_urls:
                errors.append(
                    {"chunk_id": cid, "reason": f"source_url not in allowlist: {url!r}"}
                )
            elif not row.get("chunk_id"):
                errors.append({"chunk_id": cid, "reason": "missing chunk_id"})
    return (
        not errors and total_chunks > 0,
        {
            "total_chunks": total_chunks,
            "scheme_files": len(jsonl_files),
            "errors": errors[:20],
            "error_count": len(errors),
        },
    )


def _compact_chunk_manifests(manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scheme_id": m.get("scheme_id"),
            "ok": bool(m.get("ok")),
            "chunk_count": m.get("chunk_count"),
            "error": m.get("error"),
        }
        for m in manifests
    ]


def _smoke_retrieval_hits(retriever: Retriever) -> dict[str, Any]:
    """Fail if any golden query returns zero allowlisted hits."""
    from ms02_index.p2_4_retrieval.eval import load_golden_queries

    failures: list[dict[str, str]] = []
    for item in load_golden_queries():
        q = str(item["query"])
        hits = retriever.hybrid_search(q, top_k=3)
        if not hits:
            failures.append({"id": str(item.get("id")), "query": q, "reason": "zero hits"})
    return {"ok": not failures, "failures": failures}


def run_phase2_pipeline(
    *,
    normalized_root: Path | None = None,
    chunks_root: Path | None = None,
    embeddings_root: Path | None = None,
    vector_store_root: Path | None = None,
    allowlist_path: Path | None = None,
    model_id: str = DEFAULT_MODEL_ID,
    skip_validate_sh: bool = False,
    run_tests: bool = False,
    skip_golden: bool = False,
) -> tuple[list[StepResult], bool]:
    """
    Execute 2.1→2.4 in order. Returns (steps, all_ok).
    """
    steps: list[StepResult] = []
    norm_r = normalized_root or _default_normalized_dir()
    chunks_r = chunks_root or _default_chunks_dir()
    emb_r = embeddings_root or _default_embeddings_dir()
    vs_r = vector_store_root or _default_vector_store_dir()
    allowlist = allowlist_path or _default_allowlist_path()

    if not skip_validate_sh:
        msg = run_validate_allowlist_sh()
        steps.append(StepResult("0_validate_allowlist_sh", True, {"message": msg}))

    if run_tests:
        run_unittests()
        steps.append(StepResult("0_unittest_discover", True, {}))

    registry = load_registry(allowlist)
    reg_ok = len(registry.schemes) == EXPECTED_SCHEME_COUNT
    steps.append(
        StepResult(
            "2.0_registry",
            reg_ok,
            {
                "allowlist_path": str(allowlist.resolve()),
                "schemes": len(registry.schemes),
                "expected_schemes": EXPECTED_SCHEME_COUNT,
            },
        )
    )
    if not reg_ok:
        return steps, False

    _preflight_normalized(registry, norm_r)
    steps.append(
        StepResult(
            "2.0_preflight",
            True,
            {
                "normalized_root": str(norm_r.resolve()),
                "scheme_count": len(registry.schemes),
            },
        )
    )

    try:
        chunk_manifests = chunk_all(
            registry, normalized_root=norm_r, chunks_root=chunks_r
        )
    except ChunkingError as exc:
        steps.append(StepResult("2.1_chunking", False, {"error": str(exc)}))
        return steps, False

    chunk_ok = all(m.get("ok") for m in chunk_manifests) and all(
        int(m.get("chunk_count") or 0) > 0 for m in chunk_manifests
    )
    total_chunks = sum(int(m.get("chunk_count") or 0) for m in chunk_manifests)
    steps.append(
        StepResult(
            "2.1_chunking",
            chunk_ok,
            {
                "chunks_root": str(chunks_r.resolve()),
                "total_chunks": total_chunks,
                "results": _compact_chunk_manifests(chunk_manifests),
            },
        )
    )
    if not chunk_ok:
        return steps, False

    meta_ok, meta_detail = _validate_chunks_metadata(chunks_r, registry)
    steps.append(StepResult("2.1_chunk_metadata", meta_ok, meta_detail))
    if not meta_ok:
        return steps, False

    try:
        embed_manifest = embed_all(
            chunks_root=chunks_r,
            embeddings_root=emb_r,
            model_id=model_id,
        )
    except EmbeddingError as exc:
        steps.append(StepResult("2.2_embeddings", False, {"error": str(exc)}))
        return steps, False

    embed_ok = bool(embed_manifest.get("ok")) and int(
        embed_manifest.get("total_embedded") or 0
    ) > 0
    steps.append(
        StepResult(
            "2.2_embeddings",
            embed_ok,
            {
                "embeddings_root": str(emb_r.resolve()),
                "total_embedded": embed_manifest.get("total_embedded"),
                "total_skipped": embed_manifest.get("total_skipped"),
                "embedding_model_id": embed_manifest.get("embedding_model_id"),
            },
        )
    )
    if not embed_ok:
        return steps, False

    try:
        vs_manifest = build_vector_store(
            embeddings_root=emb_r,
            vector_store_root=vs_r,
            allowlist_path=allowlist,
            recreate=True,
        )
    except VectorStoreError as exc:
        steps.append(StepResult("2.3_vector_store", False, {"error": str(exc)}))
        return steps, False

    vs_ok = bool(vs_manifest.get("ok"))
    steps.append(
        StepResult(
            "2.3_vector_store",
            vs_ok,
            {
                "vector_store_root": str(vs_r.resolve()),
                "total_vectors": vs_manifest.get("total_vectors"),
                "backend": vs_manifest.get("backend"),
                "collection_name": vs_manifest.get("collection_name"),
            },
        )
    )
    if not vs_ok:
        return steps, False

    if skip_golden:
        steps.append(
            StepResult("2.4_golden_eval", True, {"skipped": True}),
        )
        steps.append(
            StepResult("2.4_smoke_hits", True, {"skipped": True}),
        )
        return steps, True

    try:
        retriever = Retriever(
            vector_store_root=vs_r,
            allowlist_path=allowlist,
            model_id=model_id,
        )
        golden_report = run_golden_evaluation(retriever=retriever)
        smoke = _smoke_retrieval_hits(retriever)
    except (RetrievalError, EmbeddingError) as exc:
        steps.append(StepResult("2.4_retrieval", False, {"error": str(exc)}))
        return steps, False

    golden_ok = bool(golden_report.get("ok"))
    steps.append(
        StepResult(
            "2.4_golden_eval",
            golden_ok,
            {
                "hybrid_top1_accuracy": golden_report.get("hybrid_top1_accuracy"),
                "vector_top1_accuracy": golden_report.get("vector_top1_accuracy"),
                "hybrid_mean_reciprocal_rank": golden_report.get(
                    "hybrid_mean_reciprocal_rank"
                ),
                "queries_passing": golden_report.get("queries_passing"),
                "total_queries": golden_report.get("total_queries"),
            },
        )
    )

    smoke_ok = bool(smoke.get("ok"))
    steps.append(
        StepResult(
            "2.4_smoke_hits",
            smoke_ok,
            smoke,
        )
    )

    all_ok = golden_ok and smoke_ok
    steps.append(
        StepResult(
            "2.5_exit",
            all_ok,
            {
                "golden_ok": golden_ok,
                "smoke_ok": smoke_ok,
                "embedding_model_id": model_id,
            },
        )
    )
    return steps, all_ok


def _serialize_steps(steps: list[StepResult]) -> list[dict[str, Any]]:
    return [{"step": s.step, "ok": s.ok, "detail": s.detail} for s in steps]


def _write_pipeline_manifest(
    steps: list[StepResult],
    *,
    ok: bool,
    paths: dict[str, str],
) -> Path:
    out = _index_dir() / "index_build.json"
    payload = {
        "ok": ok,
        "phases_root": str(_phases_dir().resolve()),
        "index_root": str(_index_dir().resolve()),
        "paths": paths,
        "steps": _serialize_steps(steps),
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Phase 2.5 — full index pipeline (2.1–2.4 + golden checks)."
    )
    p.add_argument(
        "--skip-validate-sh",
        action="store_true",
        help="Skip phases/foundations/validate_allowlist.sh.",
    )
    p.add_argument(
        "--with-tests",
        action="store_true",
        help="Run python -m unittest discover -s tests before indexing.",
    )
    p.add_argument(
        "--skip-golden",
        action="store_true",
        help="Skip golden-query evaluation and smoke hits (not recommended for CI).",
    )
    p.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help=f"Embedding model (default: {DEFAULT_MODEL_ID}).",
    )
    p.add_argument("normalized_dir", nargs="?", default=None)
    p.add_argument("chunks_dir", nargs="?", default=None)
    p.add_argument("embeddings_dir", nargs="?", default=None)
    p.add_argument("vector_store_dir", nargs="?", default=None)
    args = p.parse_args(list(argv) if argv is not None else None)

    norm = Path(args.normalized_dir).resolve() if args.normalized_dir else None
    chunks = Path(args.chunks_dir).resolve() if args.chunks_dir else None
    emb = Path(args.embeddings_dir).resolve() if args.embeddings_dir else None
    vs = Path(args.vector_store_dir).resolve() if args.vector_store_dir else None

    try:
        steps, ok = run_phase2_pipeline(
            normalized_root=norm,
            chunks_root=chunks,
            embeddings_root=emb,
            vector_store_root=vs,
            model_id=args.model_id,
            skip_validate_sh=args.skip_validate_sh,
            run_tests=args.with_tests,
            skip_golden=args.skip_golden,
        )
    except PipelineError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    paths = {
        "normalized_root": str((norm or _default_normalized_dir()).resolve()),
        "chunks_root": str((chunks or _default_chunks_dir()).resolve()),
        "embeddings_root": str((emb or _default_embeddings_dir()).resolve()),
        "vector_store_root": str((vs or _default_vector_store_dir()).resolve()),
    }
    manifest_path = _write_pipeline_manifest(steps, ok=ok, paths=paths)

    summary: dict[str, Any] = {
        "ok": ok,
        "phases_root": str(_phases_dir()),
        "index_root": str(_index_dir()),
        "manifest_path": str(manifest_path),
        "paths": paths,
        "steps": _serialize_steps(steps),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
