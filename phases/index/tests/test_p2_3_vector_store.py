"""Tests for Phase 2.3 vector store."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ms02_corpus.p1_1_registry.registry import load_registry
from ms02_index.p2_3_vector_store.loader import (
    COLLECTION_NAME,
    chroma_metadata,
    load_embedding_rows,
    validate_chunk_row,
)


class TestValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        allowlist = (
            Path(__file__).resolve().parents[2]
            / "foundations"
            / "allowlist.yaml"
        ).resolve()
        cls.registry = load_registry(allowlist)
        cls.scheme_ids = frozenset(s.id for s in cls.registry.schemes)

    def test_valid_row_passes(self) -> None:
        entry = self.registry.schemes[0]
        row = {
            "chunk_id": f"{entry.id}_0000",
            "scheme_id": entry.id,
            "source_url": entry.url,
            "embedding": [0.1] * 4,
        }
        self.assertIsNone(
            validate_chunk_row(
                row, registry=self.registry, allowed_scheme_ids=self.scheme_ids
            )
        )

    def test_rejects_unknown_url(self) -> None:
        entry = self.registry.schemes[0]
        row = {
            "chunk_id": "x",
            "scheme_id": entry.id,
            "source_url": "https://evil.example/foo",
            "embedding": [0.1],
        }
        reason = validate_chunk_row(
            row, registry=self.registry, allowed_scheme_ids=self.scheme_ids
        )
        self.assertIn("allowlist", reason or "")

    def test_chroma_metadata_scalars_only(self) -> None:
        meta = chroma_metadata(
            {
                "chunk_id": "a",
                "scheme_id": "b",
                "char_count": 100,
                "section_heading": "### Foo",
            }
        )
        self.assertEqual(meta["char_count"], 100)
        self.assertIsInstance(meta["section_heading"], str)


class TestBuildVectorStore(unittest.TestCase):
    def test_load_into_chroma_and_filter(self) -> None:
        allowlist = (
            Path(__file__).resolve().parents[2]
            / "foundations"
            / "allowlist.yaml"
        ).resolve()
        registry = load_registry(allowlist)
        entry = registry.schemes[0]

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            emb = base / "embeddings"
            vs = base / "vector_store"
            emb.mkdir()
            (emb / "manifest.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "embedding_model_id": "test",
                        "embedding_dimensions": 4,
                        "chunks_corpus_fingerprint": "abc",
                    }
                ),
                encoding="utf-8",
            )
            row = {
                "chunk_id": f"{entry.id}_0000",
                "scheme_id": entry.id,
                "scheme_name": entry.scheme_name,
                "source_url": entry.url,
                "doc_type": "groww_scheme_page",
                "section_heading": "Facts",
                "text": "Min SIP 100",
                "char_count": 11,
                "chunk_index": 0,
                "embedding": [1.0, 0.0, 0.0, 0.0],
            }
            (emb / f"{entry.id}.jsonl").write_text(
                json.dumps(row) + "\n", encoding="utf-8"
            )

            from ms02_index.p2_3_vector_store.loader import (
                build_vector_store,
                get_collection,
                get_persistent_client,
            )

            manifest = build_vector_store(
                embeddings_root=emb,
                vector_store_root=vs,
                allowlist_path=allowlist,
            )
            self.assertTrue(manifest["ok"])
            self.assertEqual(manifest["total_vectors"], 1)

            client = get_persistent_client(vs / "chroma")
            coll = get_collection(client, name=COLLECTION_NAME)
            filtered = coll.query(
                query_embeddings=[[1.0, 0.0, 0.0, 0.0]],
                n_results=1,
                where={"scheme_id": entry.id},
                include=["metadatas"],
            )
            self.assertEqual(filtered["ids"][0][0], row["chunk_id"])
            meta = filtered["metadatas"][0][0]
            self.assertEqual(meta["source_url"], entry.url)


if __name__ == "__main__":
    unittest.main()
