"""Tests for Phase 1.3 HTML extraction."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ms02_corpus.p1_1_registry.registry import SchemeEntry
from ms02_corpus.p1_3_extraction.extractor import (
    extract_main_html_fragment,
    extract_scheme,
)


class TestExtractMainHtmlFragment(unittest.TestCase):
    def test_removes_script_and_keeps_body_text(self) -> None:
        html = """<!DOCTYPE html><html><head><title>T</title>
        <script>alert(1)</script><link rel="stylesheet" href="/x.css"/>
        </head><body><div id="__next"><p>Hello SIP 500</p></div></body></html>"""
        out = extract_main_html_fragment(html)
        self.assertNotIn("script", out.lower())
        self.assertNotIn("alert", out)
        self.assertIn("Hello SIP 500", out)
        self.assertIn("__next", out)

    def test_strips_role_navigation(self) -> None:
        html = """<html><head><title>T</title></head><body>
        <div id="__next"><div role="navigation">Menu</div><p>Body</p></div></body></html>"""
        out = extract_main_html_fragment(html)
        self.assertNotIn("Menu", out)
        self.assertIn("Body", out)

    def test_strips_header_inside_next(self) -> None:
        html = """<html><head><title>X</title></head><body>
        <div id="__next"><header><span>Nav</span></header><p>Fact</p></div>
        </body></html>"""
        out = extract_main_html_fragment(html)
        self.assertNotIn("<header>", out.lower())
        self.assertIn("Fact", out)


class TestExtractSchemeIntegration(unittest.TestCase):
    def test_manifest_on_bad_raw(self) -> None:
        entry = SchemeEntry(
            id="only",
            scheme_name="Only",
            slug="hdfc-mid-cap-fund-direct-growth",
            url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        )
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw" / entry.id
            raw.mkdir(parents=True)
            (raw / "latest.html").write_text("<html></html>", encoding="utf-8")
            (raw / "manifest.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "content_sha256": "wrong",
                        "source_url": entry.url,
                        "fetched_at": "Z",
                    }
                ),
                encoding="utf-8",
            )
            inter = Path(tmp) / "intermediate"
            m = extract_scheme(entry, raw_root=Path(tmp) / "raw", intermediate_root=inter)
            self.assertFalse(m.ok)
            self.assertIn("mismatch", m.error or "")


if __name__ == "__main__":
    unittest.main()
