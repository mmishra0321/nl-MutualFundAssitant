"""Tests for Phase 1.5 pipeline."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from ms02_corpus.p1_1_registry.registry import load_registry
from ms02_corpus.p1_5_pipeline.pipeline import (
    run_phase1_pipeline,
    run_validate_allowlist_sh,
)


class TestValidateAllowlistSh(unittest.TestCase):
    def test_runs_successfully(self) -> None:
        msg = run_validate_allowlist_sh()
        self.assertIn("allowlist OK", msg)


class TestPipelineMocked(unittest.TestCase):
    @patch("ms02_corpus.p1_5_pipeline.pipeline.normalize_all")
    @patch("ms02_corpus.p1_5_pipeline.pipeline.extract_all")
    @patch("ms02_corpus.p1_5_pipeline.pipeline.fetch_all")
    def test_pipeline_all_ok(
        self, mock_fetch: MagicMock, mock_ext: MagicMock, mock_norm: MagicMock
    ) -> None:
        reg = load_registry()
        n = len(reg.schemes)
        mock_fetch.return_value = [MagicMock(ok=True, scheme_id=f"s{i}") for i in range(n)]
        mock_ext.return_value = [MagicMock(ok=True, scheme_id=f"s{i}") for i in range(n)]
        mock_norm.return_value = [MagicMock(ok=True, scheme_id=f"s{i}") for i in range(n)]

        steps, ok = run_phase1_pipeline(skip_validate_sh=True)
        self.assertTrue(ok)
        self.assertEqual(steps[-1].step, "1.5_postflight")
        mock_fetch.assert_called_once()
        mock_ext.assert_called_once()
        mock_norm.assert_called_once()

    @patch("ms02_corpus.p1_5_pipeline.pipeline.fetch_all")
    def test_pipeline_stops_on_fetch_fail(self, mock_fetch: MagicMock) -> None:
        reg = load_registry()
        n = len(reg.schemes)
        rows = [MagicMock(ok=True, scheme_id=f"s{i}") for i in range(n)]
        rows[-1] = MagicMock(ok=False, scheme_id="bad", error="http")
        mock_fetch.return_value = rows

        steps, ok = run_phase1_pipeline(skip_validate_sh=True)
        self.assertFalse(ok)
        self.assertEqual(steps[-1].step, "1.2_fetch")


if __name__ == "__main__":
    unittest.main()
