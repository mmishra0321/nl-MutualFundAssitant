"""Tests for Phase 2.4 retrieval."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ms02_corpus.p1_1_registry.registry import load_registry
from ms02_index.p2_4_retrieval.retriever import Retriever, _rrf_fuse
from ms02_index.p2_4_retrieval.scheme_resolver import resolve_scheme_id


class TestSchemeResolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        allowlist = (
            Path(__file__).resolve().parents[2]
            / "foundations"
            / "allowlist.yaml"
        ).resolve()
        cls.registry = load_registry(allowlist)

    def test_elss(self) -> None:
        self.assertEqual(
            resolve_scheme_id("minimum SIP for HDFC ELSS", self.registry),
            "hdfc_elss_tax_saver_direct_growth",
        )

    def test_mid_cap(self) -> None:
        self.assertEqual(
            resolve_scheme_id("exit load HDFC Mid Cap", self.registry),
            "hdfc_mid_cap_direct_growth",
        )

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(resolve_scheme_id("what is a mutual fund", self.registry))


class TestRRF(unittest.TestCase):
    def test_fusion_prefers_both_lists(self) -> None:
        scores = _rrf_fuse([["a", "b", "c"], ["b", "a", "d"]])
        self.assertGreater(scores["a"], scores["c"])
        self.assertGreater(scores["b"], scores["d"])


class TestRetrieverMocked(unittest.TestCase):
    @patch("ms02_index.p2_4_retrieval.retriever.load_sentence_transformer")
    @patch("ms02_index.p2_4_retrieval.retriever.get_collection")
    @patch("ms02_index.p2_4_retrieval.retriever.get_persistent_client")
    @patch("ms02_index.p2_4_retrieval.retriever._load_store_manifest")
    def test_hybrid_merges(
        self, mock_manifest, mock_client, mock_get_coll, mock_model
    ) -> None:
        allowlist = (
            Path(__file__).resolve().parents[2]
            / "foundations"
            / "allowlist.yaml"
        ).resolve()
        registry = load_registry(allowlist)
        entry = registry.schemes[0]

        mock_manifest.return_value = {
            "ok": True,
            "persist_path": "chroma",
            "collection_name": "ms02_chunks",
            "embedding_model_id": "test-model",
        }
        model = MagicMock()
        model.encode.return_value = [[1.0, 0.0]]
        mock_model.return_value = model

        collection = MagicMock()
        collection.count.return_value = 2
        collection.query.return_value = {
            "ids": [[f"{entry.id}_0000", f"{entry.id}_0001"]],
            "metadatas": [
                [
                    {
                        "scheme_id": entry.id,
                        "scheme_name": entry.scheme_name,
                        "source_url": entry.url,
                        "section_heading": "Facts",
                    },
                    {
                        "scheme_id": entry.id,
                        "scheme_name": entry.scheme_name,
                        "source_url": entry.url,
                        "section_heading": "Other",
                    },
                ]
            ],
            "documents": [["Min SIP 100", "Generic text"]],
            "distances": [[0.1, 0.5]],
        }
        collection.get.return_value = {
            "ids": [f"{entry.id}_0000", f"{entry.id}_0001"],
            "documents": ["Min SIP 100 expense ratio", "Generic text"],
            "metadatas": [
                {
                    "scheme_id": entry.id,
                    "scheme_name": entry.scheme_name,
                    "source_url": entry.url,
                    "section_heading": "Facts",
                },
                {
                    "scheme_id": entry.id,
                    "scheme_name": entry.scheme_name,
                    "source_url": entry.url,
                    "section_heading": "Other",
                },
            ],
        }
        mock_get_coll.return_value = collection

        with tempfile.TemporaryDirectory() as tmp:
            vs = Path(tmp)
            (vs / "chroma").mkdir()
            (vs / "manifest.json").write_text("{}", encoding="utf-8")
            retriever = Retriever(
                vector_store_root=vs, allowlist_path=allowlist, model_id="test"
            )
            hits = retriever.hybrid_search("minimum SIP", top_k=2)
            self.assertTrue(hits)
            self.assertEqual(hits[0].scheme_id, entry.id)
            self.assertIn(hits[0].source_url, registry.url_set())


if __name__ == "__main__":
    unittest.main()
