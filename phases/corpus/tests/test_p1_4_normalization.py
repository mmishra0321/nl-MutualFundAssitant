"""Tests for Phase 1.4 normalization."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ms02_corpus.p1_1_registry.registry import SchemeEntry
from ms02_corpus.p1_4_normalization.normalizer import (
    html_fragment_to_markdown,
    normalize_scheme,
)


class TestHtmlToMarkdown(unittest.TestCase):
    def test_basic_headings_and_list(self) -> None:
        html = "<html><body><h2>Section</h2><ul><li>One</li><li>Two</li></ul></body></html>"
        md = html_fragment_to_markdown(html)
        self.assertIn("## Section", md)
        self.assertIn("- One", md)


class TestNormalizeScheme(unittest.TestCase):
    def _entry(self) -> SchemeEntry:
        return SchemeEntry(
            id="test_scheme",
            scheme_name="Test Scheme",
            slug="hdfc-mid-cap-fund-direct-growth",
            url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        )

    def test_happy_path(self) -> None:
        entry = self._entry()
        allow = frozenset({entry.url})
        html = "<html><body><h1>Title</h1><p>Expense ratio 0.5%</p></body></html>"
        raw_bytes = b"<raw>original</raw>"
        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        ex_bytes = html.encode("utf-8")
        ex_sha = hashlib.sha256(ex_bytes).hexdigest()

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raw = base / "raw" / entry.id
            inter = base / "intermediate" / entry.id
            norm = base / "normalized"
            raw.mkdir(parents=True)
            inter.mkdir(parents=True)
            (raw / "latest.html").write_bytes(raw_bytes)
            (inter / "extracted.html").write_bytes(ex_bytes)
            (inter / "manifest.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "source_url": entry.url,
                        "raw_content_sha256": raw_sha,
                        "raw_fetched_at": "2026-01-01T00:00:00Z",
                        "extracted_sha256": ex_sha,
                        "extracted_at": "2026-01-01T01:00:00Z",
                    }
                ),
                encoding="utf-8",
            )

            m = normalize_scheme(
                entry,
                allowlist_urls=allow,
                intermediate_root=base / "intermediate",
                normalized_root=norm,
                raw_root=base / "raw",
            )
            self.assertTrue(m.ok, m.error)
            page = norm / entry.id / "page.md"
            self.assertTrue(page.is_file())
            self.assertIn("Expense ratio", page.read_text(encoding="utf-8"))
            self.assertEqual(m.raw_content_sha256, raw_sha)

    def test_extracted_hash_mismatch(self) -> None:
        entry = self._entry()
        allow = frozenset({entry.url})
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raw = base / "raw" / entry.id
            inter = base / "intermediate" / entry.id
            raw.mkdir(parents=True)
            inter.mkdir(parents=True)
            (raw / "latest.html").write_bytes(b"x")
            (inter / "extracted.html").write_text("<p>Hi</p>", encoding="utf-8")
            (inter / "manifest.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "source_url": entry.url,
                        "raw_content_sha256": hashlib.sha256(b"x").hexdigest(),
                        "raw_fetched_at": "Z",
                        "extracted_sha256": "0" * 64,
                        "extracted_at": "Z",
                    }
                ),
                encoding="utf-8",
            )
            m = normalize_scheme(
                entry,
                allowlist_urls=allow,
                intermediate_root=base / "intermediate",
                normalized_root=base / "normalized",
                raw_root=base / "raw",
            )
            self.assertFalse(m.ok)
            self.assertIn("mismatch", m.error or "")


if __name__ == "__main__":
    unittest.main()
