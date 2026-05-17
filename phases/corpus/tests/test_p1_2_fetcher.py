"""Tests for Phase 1.2 raw fetcher."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from ms02_corpus.p1_1_registry.registry import SchemeEntry, load_registry
from ms02_corpus.p1_2_fetcher.fetcher import (
    FetcherError,
    _canonical_groww_page_url,
    _validate_final_url,
    fetch_scheme_raw,
)


class TestCanonicalUrl(unittest.TestCase):
    def test_www_normalized(self) -> None:
        u = "https://www.groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
        self.assertEqual(
            _canonical_groww_page_url(u),
            "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        )

    def test_reject_other_host(self) -> None:
        with self.assertRaises(FetcherError):
            _canonical_groww_page_url("https://evil.com/mutual-funds/x")

    def test_reject_query(self) -> None:
        with self.assertRaises(FetcherError):
            _canonical_groww_page_url(
                "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth?utm=1"
            )


class TestValidateFinalUrl(unittest.TestCase):
    def test_ok(self) -> None:
        entry = SchemeEntry(
            id="x",
            scheme_name="n",
            slug="hdfc-mid-cap-fund-direct-growth",
            url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        )
        allow = frozenset({entry.url})
        self.assertEqual(
            _validate_final_url(entry, entry.url, allow),
            entry.url,
        )

    def test_wrong_scheme_path(self) -> None:
        entry = SchemeEntry(
            id="x",
            scheme_name="n",
            slug="hdfc-large-cap-fund-direct-growth",
            url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        )
        allow = frozenset(
            {
                "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                entry.url,
            }
        )
        with self.assertRaises(FetcherError):
            _validate_final_url(
                entry,
                "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                allow,
            )


class TestFetchSchemeRawMocked(unittest.TestCase):
    def test_writes_html_and_manifest(self) -> None:
        reg = load_registry()
        entry = reg.schemes[0]
        allow = reg.url_set()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = entry.url
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.content = b"<html><title>test</title></html>"

        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp)
            session = MagicMock()
            session.get.return_value = mock_resp

            m = fetch_scheme_raw(entry, allowlist_urls=allow, session=session, raw_root=raw_root)

            self.assertTrue(m.ok)
            html = raw_root / entry.id / "latest.html"
            man = raw_root / entry.id / "manifest.json"
            self.assertTrue(html.is_file())
            self.assertTrue(man.is_file())
            data = json.loads(man.read_text(encoding="utf-8"))
            self.assertEqual(data["scheme_id"], entry.id)
            self.assertTrue(data["content_sha256"])
            session.get.assert_called_once()

    def test_pdf_content_type_fails(self) -> None:
        reg = load_registry()
        entry = reg.schemes[0]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = entry.url
        mock_resp.headers = {"Content-Type": "application/pdf"}
        mock_resp.content = b"%PDF-1.4"

        with tempfile.TemporaryDirectory() as tmp:
            raw_root = Path(tmp)
            session = MagicMock()
            session.get.return_value = mock_resp

            m = fetch_scheme_raw(
                entry, allowlist_urls=reg.url_set(), session=session, raw_root=raw_root
            )
            self.assertFalse(m.ok)
            self.assertIn("PDF", m.error or "")


if __name__ == "__main__":
    unittest.main()
