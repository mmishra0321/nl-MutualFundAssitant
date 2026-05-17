"""
Phase 2.2 — Embeddings (phased-architecture.md).

Batch-embed Phase 2.1 chunks; record embedding_model_id and dimensions.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

DEFAULT_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MIN_CHARS_TO_EMBED = 40
BATCH_SIZE = 32


class EmbeddingError(RuntimeError):
    """Chunk load or embedding failure."""


@dataclass(frozen=True)
class SkippedChunk:
    chunk_id: str
    scheme_id: str
    reason: str
    char_count: int


def _default_chunks_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "chunks"


def _default_embeddings_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "embeddings"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _chunks_corpus_fingerprint(chunks_root: Path) -> str:
    """SHA-256 over sorted scheme jsonl file hashes (reproducibility)."""
    h = hashlib.sha256()
    for path in sorted(chunks_root.glob("*.jsonl")):
        if path.name == "index.json":
            continue
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def embedding_input_text(chunk: dict[str, Any]) -> str:
    """Text passed to the embedding model (scheme + heading disambiguation)."""
    return (
        f"{chunk['scheme_name']} | {chunk['section_heading']}\n"
        f"{chunk['text']}"
    ).strip()


def should_skip_chunk(chunk: dict[str, Any]) -> str | None:
    text = (chunk.get("text") or "").strip()
    if len(text) < MIN_CHARS_TO_EMBED:
        return f"text shorter than {MIN_CHARS_TO_EMBED} characters"
    # Heading-only: body equals heading line with no extra content
    heading = (chunk.get("section_heading") or "").strip()
    if heading and text.replace(heading, "").strip() in ("", "See All"):
        if len(text) < 80:
            return "heading-only or boilerplate fragment"
    return None


def load_sentence_transformer(model_id: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingError(
            "sentence-transformers not installed; pip install -r requirements.txt"
        ) from exc
    return SentenceTransformer(model_id)


def embed_texts(model, texts: list[str]) -> np.ndarray:
    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(vectors, dtype=np.float32)


def embed_scheme_file(
    jsonl_path: Path,
    *,
    model,
    embeddings_root: Path,
) -> tuple[int, int, list[SkippedChunk]]:
    chunks = _read_jsonl(jsonl_path)
    scheme_id = jsonl_path.stem
    to_embed: list[dict[str, Any]] = []
    skipped: list[SkippedChunk] = []

    for ch in chunks:
        reason = should_skip_chunk(ch)
        if reason:
            skipped.append(
                SkippedChunk(
                    chunk_id=str(ch["chunk_id"]),
                    scheme_id=str(ch.get("scheme_id", scheme_id)),
                    reason=reason,
                    char_count=int(ch.get("char_count", 0)),
                )
            )
        else:
            to_embed.append(ch)

    out_path = embeddings_root / f"{scheme_id}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not to_embed:
        out_path.write_text("", encoding="utf-8")
        return 0, len(skipped), skipped

    texts = [embedding_input_text(c) for c in to_embed]
    vectors = embed_texts(model, texts)

    with out_path.open("w", encoding="utf-8") as fh:
        for ch, vec in zip(to_embed, vectors):
            row = dict(ch)
            row["embedding"] = vec.tolist()
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(to_embed), len(skipped), skipped


def embed_all(
    *,
    chunks_root: Path | None = None,
    embeddings_root: Path | None = None,
    model_id: str = DEFAULT_MODEL_ID,
) -> dict[str, Any]:
    chunks_r = chunks_root or _default_chunks_dir()
    emb_r = embeddings_root or _default_embeddings_dir()
    emb_r.mkdir(parents=True, exist_ok=True)

    jsonl_files = sorted(chunks_r.glob("*.jsonl"))
    scheme_files = [p for p in jsonl_files if not p.name.endswith(".manifest.json")]
    if not scheme_files:
        raise EmbeddingError(f"No chunk JSONL files under {chunks_r}")

    model = load_sentence_transformer(model_id)
    dim = int(model.get_sentence_embedding_dimension())

    total_embedded = 0
    total_skipped = 0
    all_skipped: list[SkippedChunk] = []
    per_scheme: list[dict[str, Any]] = []

    for path in scheme_files:
        n_emb, n_skip, skipped = embed_scheme_file(
            path, model=model, embeddings_root=emb_r
        )
        total_embedded += n_emb
        total_skipped += n_skip
        all_skipped.extend(skipped)
        per_scheme.append(
            {
                "scheme_id": path.stem,
                "embedded_count": n_emb,
                "skipped_count": n_skip,
                "embeddings_file": f"{path.stem}.jsonl",
            }
        )

    embedded_at = (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    manifest: dict[str, Any] = {
        "ok": total_embedded > 0,
        "embedding_model_id": model_id,
        "embedding_dimensions": dim,
        "embedded_at": embedded_at,
        "chunks_root": str(chunks_r.resolve()),
        "embeddings_root": str(emb_r.resolve()),
        "chunks_corpus_fingerprint": _chunks_corpus_fingerprint(chunks_r),
        "total_embedded": total_embedded,
        "total_skipped": total_skipped,
        "schemes": per_scheme,
        "error": None if total_embedded > 0 else "no chunks embedded",
    }
    (emb_r / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if all_skipped:
        with (emb_r / "skipped.jsonl").open("w", encoding="utf-8") as fh:
            for s in all_skipped:
                fh.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    chunks_dir: Path | None = None
    emb_dir: Path | None = None
    model_id = DEFAULT_MODEL_ID
    if len(argv) >= 1:
        chunks_dir = Path(argv[0]).resolve()
    if len(argv) >= 2:
        emb_dir = Path(argv[1]).resolve()
    if len(argv) >= 3:
        model_id = argv[2]

    try:
        manifest = embed_all(
            chunks_root=chunks_dir,
            embeddings_root=emb_dir,
            model_id=model_id,
        )
    except EmbeddingError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
