"""Tests for Phase 2.5 index pipeline."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ms02_corpus.p1_1_registry.registry import load_registry
from ms02_index.p2_5_pipeline.pipeline import (
    PipelineError,
    _preflight_normalized,
    run_phase2_pipeline,
)


class TestPreflight(unittest.TestCase):
    def test_missing_normalized_raises(self) -> None:
        allowlist = (
            Path(__file__).resolve().parents[2]
            / "foundations"
            / "allowlist.yaml"
        ).resolve()
        registry = load_registry(allowlist)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PipelineError):
                _preflight_normalized(registry, Path(tmp))


class TestPipelineMocked(unittest.TestCase):
    @patch("ms02_index.p2_5_pipeline.pipeline.Retriever")
    @patch("ms02_index.p2_5_pipeline.pipeline._smoke_retrieval_hits")
    @patch("ms02_index.p2_5_pipeline.pipeline.run_golden_evaluation")
    @patch("ms02_index.p2_5_pipeline.pipeline.build_vector_store")
    @patch("ms02_index.p2_5_pipeline.pipeline.embed_all")
    @patch("ms02_index.p2_5_pipeline.pipeline._validate_chunks_metadata")
    @patch("ms02_index.p2_5_pipeline.pipeline.chunk_all")
    @patch("ms02_index.p2_5_pipeline.pipeline.run_validate_allowlist_sh")
    def test_full_pipeline_ok(
        self,
        mock_validate,
        mock_chunk,
        mock_validate_chunks,
        mock_embed,
        mock_vs,
        mock_golden,
        mock_smoke,
        mock_retriever_cls,
    ) -> None:
        allowlist = (
            Path(__file__).resolve().parents[2]
            / "foundations"
            / "allowlist.yaml"
        ).resolve()
        registry = load_registry(allowlist)

        mock_validate.return_value = "allowlist OK"
        mock_chunk.return_value = [
            {"scheme_id": e.id, "ok": True, "chunk_count": 10}
            for e in registry.schemes
        ]
        mock_validate_chunks.return_value = (True, {"total_chunks": 50, "error_count": 0})
        mock_embed.return_value = {
            "ok": True,
            "total_embedded": 18,
            "total_skipped": 0,
            "embedding_model_id": "test",
        }
        mock_vs.return_value = {
            "ok": True,
            "total_vectors": 18,
            "backend": "chromadb",
            "collection_name": "ms02_chunks",
        }
        mock_golden.return_value = {
            "ok": True,
            "hybrid_top1_accuracy": 1.0,
            "vector_top1_accuracy": 0.8,
            "hybrid_mean_reciprocal_rank": 1.0,
            "queries_passing": 2,
            "total_queries": 2,
        }
        mock_smoke.return_value = {"ok": True, "failures": []}
        mock_retriever_cls.return_value = object()

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            norm = base / "normalized"
            norm.mkdir()
            for entry in registry.schemes:
                scheme_dir = norm / entry.id
                scheme_dir.mkdir()
                (scheme_dir / "page.md").write_text("# Test\n\nBody", encoding="utf-8")

            steps, ok = run_phase2_pipeline(
                normalized_root=norm,
                chunks_root=base / "chunks",
                embeddings_root=base / "embeddings",
                vector_store_root=base / "vector_store",
                allowlist_path=allowlist,
                skip_validate_sh=True,
            )
            self.assertTrue(ok)
            step_names = [s.step for s in steps]
            self.assertIn("2.1_chunking", step_names)
            self.assertIn("2.1_chunk_metadata", step_names)
            self.assertIn("2.4_golden_eval", step_names)
            self.assertIn("2.5_exit", step_names)
            mock_chunk.assert_called_once()
            mock_embed.assert_called_once()
            mock_vs.assert_called_once()
            mock_golden.assert_called_once()


if __name__ == "__main__":
    unittest.main()
