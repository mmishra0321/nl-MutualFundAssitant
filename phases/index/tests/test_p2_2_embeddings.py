"""Tests for Phase 2.2 embeddings."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from ms02_index.p2_2_embeddings.embedder import (
    embed_all,
    embedding_input_text,
    should_skip_chunk,
)


class TestEmbeddingHelpers(unittest.TestCase):
    def test_embedding_input_text(self) -> None:
        ch = {
            "scheme_name": "HDFC Mid Cap",
            "section_heading": "### Minimum investments",
            "text": "Min. for SIP ₹100",
        }
        t = embedding_input_text(ch)
        self.assertIn("HDFC Mid Cap", t)
        self.assertIn("Minimum investments", t)
        self.assertIn("₹100", t)

    def test_skip_short_chunk(self) -> None:
        ch = {"section_heading": "X", "text": "See All", "char_count": 7}
        self.assertIsNotNone(should_skip_chunk(ch))

    def test_do_not_skip_factual(self) -> None:
        ch = {
            "section_heading": "### Exit Load",
            "text": "### Exit Load\n\nExit load of 1% if redeemed within 1 year.",
            "char_count": 68,
        }
        self.assertIsNone(should_skip_chunk(ch))


class TestEmbedAllMocked(unittest.TestCase):
    @patch("ms02_index.p2_2_embeddings.embedder.load_sentence_transformer")
    def test_embed_writes_vectors(self, mock_load: MagicMock) -> None:
        model = MagicMock()
        model.get_sentence_embedding_dimension.return_value = 4
        model.encode.return_value = np.array(
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float32
        )
        mock_load.return_value = model

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            chunks = base / "chunks"
            emb = base / "embeddings"
            chunks.mkdir()
            (chunks / "test_scheme.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "chunk_id": "test_scheme_0000",
                                "scheme_id": "test_scheme",
                                "scheme_name": "Test",
                                "section_heading": "Facts",
                                "text": "Expense ratio 0.5% and minimum SIP 100 rupees",
                                "char_count": 50,
                            }
                        ),
                        json.dumps(
                            {
                                "chunk_id": "test_scheme_0001",
                                "scheme_id": "test_scheme",
                                "scheme_name": "Test",
                                "section_heading": "Tiny",
                                "text": "Hi",
                                "char_count": 2,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            manifest = embed_all(chunks_root=chunks, embeddings_root=emb)
            self.assertTrue(manifest["ok"])
            self.assertEqual(manifest["embedding_dimensions"], 4)
            self.assertEqual(manifest["total_embedded"], 1)
            self.assertEqual(manifest["total_skipped"], 1)
            out = emb / "test_scheme.jsonl"
            self.assertTrue(out.is_file())
            row = json.loads(out.read_text(encoding="utf-8").strip())
            self.assertEqual(len(row["embedding"]), 4)


if __name__ == "__main__":
    unittest.main()
