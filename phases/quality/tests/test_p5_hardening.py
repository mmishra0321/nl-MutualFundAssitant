"""Unit tests for Quality gates utilities."""

from __future__ import annotations

import unittest
from pathlib import Path

from ms02_hardening.checks.handoff import (
    DISCLAIMER_TEXT,
    check_disclaimer_artifacts,
)
from ms02_hardening.logging_policy import sanitize_for_log


class TestLoggingPolicy(unittest.TestCase):
    def test_redacts_email_and_pan(self) -> None:
        raw = "Email user@example.com PAN ABCDE1234F"
        out = sanitize_for_log(raw)
        self.assertNotIn("user@example.com", out)
        self.assertIn("[REDACTED]", out)

    def test_truncates_long_text(self) -> None:
        out = sanitize_for_log("x" * 500, max_len=50)
        self.assertLessEqual(len(out), 50)


class TestHandoff(unittest.TestCase):
    def test_disclaimer_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        report = check_disclaimer_artifacts(root)
        self.assertTrue(report["ok"], report)
        txt = (root / "disclaimer" / "disclaimer.txt").read_text(encoding="utf-8")
        self.assertEqual(txt.strip(), DISCLAIMER_TEXT)


if __name__ == "__main__":
    unittest.main()
