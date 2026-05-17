"""
Phase 2.3 — Vector store (phased-architecture.md).

Load Phase 2.2 embeddings into a local Chroma collection scoped to the five
allowlisted schemes. Validates source_url against Phase 0 before insert.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from ms02_corpus.p1_1_registry.registry import Registry, load_registry

COLLECTION_NAME = "ms02_chunks"
BACKEND = "chromadb"
BATCH_SIZE = 64

# Scalar metadata stored in Chroma (documents hold chunk text).
_METADATA_KEYS = (
    "chunk_id",
    "scheme_id",
    "scheme_name",
    "source_url",
    "doc_type",
    "section_heading",
    "char_count",
    "chunk_index",
    "raw_fetched_at",
    "normalized_at",
)


class VectorStoreError(RuntimeError):
    """Load, validation, or Chroma failure."""


@dataclass(frozen=True)
class RejectedRow:
    chunk_id: str
    scheme_id: str
    reason: str


def _default_embeddings_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "embeddings"


def _default_vector_store_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "vector_store"


def _default_allowlist_path() -> Path:
    return Path(__file__).resolve().parents[3] / "foundations" / "allowlist.yaml"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_embeddings_manifest(embeddings_root: Path) -> dict[str, Any]:
    manifest_path = embeddings_root / "manifest.json"
    if not manifest_path.is_file():
        raise VectorStoreError(f"Missing embeddings manifest: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _scheme_ids_from_registry(registry: Registry) -> frozenset[str]:
    return frozenset(s.id for s in registry.schemes)


def validate_chunk_row(
    row: dict[str, Any],
    *,
    registry: Registry,
    allowed_scheme_ids: frozenset[str],
) -> str | None:
    source_url = (row.get("source_url") or "").strip()
    if source_url not in registry.url_set():
        return f"source_url not in allowlist: {source_url!r}"
    scheme_id = (row.get("scheme_id") or "").strip()
    if scheme_id not in allowed_scheme_ids:
        return f"scheme_id not in allowlist: {scheme_id!r}"
    entry = next((s for s in registry.schemes if s.id == scheme_id), None)
    if entry and entry.url != source_url:
        return f"source_url {source_url!r} does not match scheme {scheme_id!r}"
    if "embedding" not in row or not isinstance(row["embedding"], list):
        return "missing embedding vector"
    if not row["embedding"]:
        return "empty embedding vector"
    return None


def chroma_metadata(row: dict[str, Any]) -> dict[str, str | int | float | bool]:
    meta: dict[str, str | int | float | bool] = {}
    for key in _METADATA_KEYS:
        if key not in row:
            continue
        val = row[key]
        if isinstance(val, bool):
            meta[key] = val
        elif isinstance(val, int):
            meta[key] = val
        elif isinstance(val, float):
            meta[key] = val
        elif isinstance(val, str):
            meta[key] = val
        else:
            meta[key] = str(val)
    return meta


def load_embedding_rows(
    embeddings_root: Path,
    *,
    registry: Registry,
) -> tuple[list[dict[str, Any]], list[RejectedRow]]:
    emb_manifest = _load_embeddings_manifest(embeddings_root)
    if not emb_manifest.get("ok"):
        raise VectorStoreError(
            f"Embeddings manifest not ok: {emb_manifest.get('error')}"
        )

    allowed_scheme_ids = _scheme_ids_from_registry(registry)
    accepted: list[dict[str, Any]] = []
    rejected: list[RejectedRow] = []

    jsonl_files = sorted(embeddings_root.glob("*.jsonl"))
    for path in jsonl_files:
        if path.name == "skipped.jsonl":
            continue
        for row in _read_jsonl(path):
            reason = validate_chunk_row(
                row, registry=registry, allowed_scheme_ids=allowed_scheme_ids
            )
            if reason:
                rejected.append(
                    RejectedRow(
                        chunk_id=str(row.get("chunk_id", path.stem)),
                        scheme_id=str(row.get("scheme_id", path.stem)),
                        reason=reason,
                    )
                )
            else:
                accepted.append(row)

    if not accepted:
        raise VectorStoreError("No valid embedding rows to load")

    return accepted, rejected, emb_manifest


def _import_chromadb():
    try:
        import chromadb
    except ImportError as exc:
        raise VectorStoreError(
            "chromadb not installed; pip install -r requirements.txt"
        ) from exc
    return chromadb


def get_persistent_client(persist_dir: Path):
    chromadb = _import_chromadb()
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir.resolve()))


def get_collection(client, *, name: str = COLLECTION_NAME):
    return client.get_collection(name=name)


def load_into_chroma(
    rows: list[dict[str, Any]],
    *,
    persist_dir: Path,
    collection_name: str = COLLECTION_NAME,
    recreate: bool = True,
) -> Any:
    """Upsert all rows into Chroma; returns the collection."""
    chromadb = _import_chromadb()
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir.resolve()))

    if recreate:
        try:
            client.delete_collection(collection_name)
        except (ValueError, Exception):
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        collection.add(
            ids=[str(r["chunk_id"]) for r in batch],
            embeddings=[r["embedding"] for r in batch],
            documents=[str(r.get("text") or "") for r in batch],
            metadatas=[chroma_metadata(r) for r in batch],
        )

    return collection


def probe_collection(collection, *, dimensions: int) -> dict[str, Any]:
    """Sanity query: verify store returns hits with allowlisted metadata."""
    probe = [0.0] * dimensions
    probe[0] = 1.0
    result = collection.query(
        query_embeddings=[probe],
        n_results=min(3, collection.count()),
        include=["metadatas", "documents", "distances"],
    )
    return {
        "count": collection.count(),
        "sample_ids": (result.get("ids") or [[]])[0][:3],
        "sample_scheme_ids": [
            m.get("scheme_id")
            for m in (result.get("metadatas") or [[]])[0][:3]
        ],
    }


def build_vector_store(
    *,
    embeddings_root: Path | None = None,
    vector_store_root: Path | None = None,
    allowlist_path: Path | None = None,
    recreate: bool = True,
) -> dict[str, Any]:
    emb_r = embeddings_root or _default_embeddings_dir()
    vs_r = vector_store_root or _default_vector_store_dir()
    allowlist = allowlist_path or _default_allowlist_path()

    registry = load_registry(allowlist)
    rows, rejected, emb_manifest = load_embedding_rows(emb_r, registry=registry)

    chroma_dir = vs_r / "chroma"
    collection = load_into_chroma(
        rows, persist_dir=chroma_dir, recreate=recreate
    )

    dim = int(emb_manifest.get("embedding_dimensions", len(rows[0]["embedding"])))
    probe = probe_collection(collection, dimensions=dim)

    per_scheme: dict[str, int] = {}
    for r in rows:
        sid = str(r["scheme_id"])
        per_scheme[sid] = per_scheme.get(sid, 0) + 1

    loaded_at = (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    manifest: dict[str, Any] = {
        "ok": collection.count() == len(rows),
        "backend": BACKEND,
        "collection_name": COLLECTION_NAME,
        "persist_path": str(chroma_dir.resolve()),
        "embeddings_root": str(emb_r.resolve()),
        "allowlist_path": str(allowlist.resolve()),
        "embedding_model_id": emb_manifest.get("embedding_model_id"),
        "embedding_dimensions": dim,
        "chunks_corpus_fingerprint": emb_manifest.get("chunks_corpus_fingerprint"),
        "total_vectors": collection.count(),
        "total_rejected": len(rejected),
        "schemes": [
            {"scheme_id": sid, "vector_count": per_scheme[sid]}
            for sid in sorted(per_scheme)
        ],
        "probe": probe,
        "loaded_at": loaded_at,
        "error": None if collection.count() == len(rows) else "vector count mismatch",
    }

    vs_r.mkdir(parents=True, exist_ok=True)
    (vs_r / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if rejected:
        with (vs_r / "rejected.jsonl").open("w", encoding="utf-8") as fh:
            for r in rejected:
                fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    emb_dir: Path | None = None
    vs_dir: Path | None = None
    allowlist: Path | None = None
    if len(argv) >= 1:
        emb_dir = Path(argv[0]).resolve()
    if len(argv) >= 2:
        vs_dir = Path(argv[1]).resolve()
    if len(argv) >= 3:
        allowlist = Path(argv[2]).resolve()

    try:
        manifest = build_vector_store(
            embeddings_root=emb_dir,
            vector_store_root=vs_dir,
            allowlist_path=allowlist,
        )
    except VectorStoreError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
