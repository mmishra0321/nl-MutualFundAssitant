"""Tests for Phase 2.1 chunking."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ms02_corpus.p1_1_registry.registry import SchemeEntry
from ms02_index.p2_1_chunking.chunker import (
    chunk_scheme,
    chunk_text,
)


class TestChunkText(unittest.TestCase):
    def test_heading_sections(self) -> None:
        md = """## Fund facts
Min. for SIP ₹100
Expense ratio 0.80%

## Exit load
Exit load of 1% if redeemed within 1 year.
"""
        prov = {
            "raw_fetched_at": "Z",
            "raw_content_sha256": "a",
            "normalized_sha256": "b",
            "normalized_at": "Z",
        }
        recs = chunk_text(
            md,
            scheme_id="test",
            scheme_name="Test",
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            provenance=prov,
        )
        self.assertGreaterEqual(len(recs), 2)
        texts = " ".join(r.text for r in recs)
        self.assertIn("Expense ratio", texts)
        self.assertIn("Exit load", texts)

    def test_table_not_split_mid_row(self) -> None:
        md = """## Holdings
| A | B |
| --- | --- |
| 1 | 2 |
| 3 | 4 |
"""
        prov = {
            "raw_fetched_at": "Z",
            "raw_content_sha256": "a",
            "normalized_sha256": "b",
            "normalized_at": "Z",
        }
        recs = chunk_text(
            md,
            scheme_id="test",
            scheme_name="Test",
            source_url="https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
            provenance=prov,
        )
        table_chunks = [r for r in recs if "| 1 |" in r.text]
        self.assertEqual(len(table_chunks), 1)
        self.assertIn("| 3 |", table_chunks[0].text)

    def test_sip_and_expense_in_same_section(self) -> None:
        md = """### Minimum investments
Min. for SIP ₹100
Min. for 1st investment ₹100
"""
        prov = {
            "raw_fetched_at": "Z",
            "raw_content_sha256": "a",
            "normalized_sha256": "b",
            "normalized_at": "Z",
        }
        recs = chunk_text(
            md,
            scheme_id="test",
            scheme_name="Test",
            source_url="https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
            provenance=prov,
        )
        self.assertEqual(len(recs), 1)
        self.assertIn("Min. for SIP", recs[0].text)
        self.assertIn("Min. for 1st investment", recs[0].text)


class TestChunkSchemeIntegration(unittest.TestCase):
    def test_writes_jsonl(self) -> None:
        entry = SchemeEntry(
            id="test_scheme",
            scheme_name="Test",
            slug="hdfc-mid-cap-fund-direct-growth",
            url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        )
        allow = frozenset({entry.url})
        md = "## Facts\nExpense ratio 0.5%\nMin. for SIP ₹100\n"
        import hashlib

        sha = hashlib.sha256(md.encode()).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            norm = base / "normalized" / entry.id
            chunks = base / "chunks"
            norm.mkdir(parents=True)
            (norm / "page.md").write_text(md, encoding="utf-8")
            (norm / "manifest.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "source_url": entry.url,
                        "raw_fetched_at": "2026-01-01T00:00:00Z",
                        "raw_content_sha256": "raw",
                        "normalized_sha256": sha,
                        "normalized_at": "2026-01-01T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            man = chunk_scheme(
                entry,
                allowlist_urls=allow,
                normalized_root=base / "normalized",
                chunks_root=chunks,
            )
            self.assertTrue(man["ok"])
            self.assertGreater(man["chunk_count"], 0)
            jsonl = chunks / f"{entry.id}.jsonl"
            self.assertTrue(jsonl.is_file())
            line = json.loads(jsonl.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(line["source_url"], entry.url)
            self.assertEqual(line["scheme_id"], entry.id)


if __name__ == "__main__":
    unittest.main()
