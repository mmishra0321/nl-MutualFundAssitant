"""Unit tests for Phase 1.1 registry."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from ms02_corpus.p1_1_registry.registry import (
    CANONICAL_URLS,
    RegistryError,
    build_registry,
    load_registry,
)


def _repo_phases_dir() -> Path:
    # tests/ -> corpus -> phases
    return Path(__file__).resolve().parents[2]


def _write_yaml(tmp: Path, payload: dict) -> Path:
    p = tmp / "allowlist.yaml"
    p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return p


class TestP11Registry(unittest.TestCase):
    def test_load_default_allowlist_ok(self) -> None:
        reg = load_registry()
        self.assertEqual(len(reg.schemes), 5)
        self.assertEqual(reg.url_set(), CANONICAL_URLS)
        self.assertEqual(reg.amc, "HDFC")

    def test_unknown_url_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            urls = [
                {
                    "id": "a",
                    "scheme_name": "A",
                    "slug": "hdfc-mid-cap-fund-direct-growth",
                    "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                },
                {
                    "id": "b",
                    "scheme_name": "B",
                    "slug": "hdfc-equity-fund-direct-growth",
                    "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
                },
                {
                    "id": "c",
                    "scheme_name": "C",
                    "slug": "hdfc-focused-fund-direct-growth",
                    "url": "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
                },
                {
                    "id": "d",
                    "scheme_name": "D",
                    "slug": "hdfc-elss-tax-saver-fund-direct-plan-growth",
                    "url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
                },
                {
                    "id": "e",
                    "scheme_name": "E",
                    "slug": "wrong-slug",
                    "url": "https://groww.in/mutual-funds/wrong-slug",
                },
            ]
            path = _write_yaml(
                Path(tmp),
                {"version": 1, "amc": "HDFC", "description": "x", "urls": urls},
            )
            with self.assertRaises(RegistryError):
                load_registry(path)

    def test_slug_url_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good = [
                {
                    "id": "hdfc_mid_cap_direct_growth",
                    "scheme_name": "HDFC Mid Cap Fund Direct Growth",
                    "slug": "hdfc-mid-cap-fund-direct-growth",
                    "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                },
                {
                    "id": "hdfc_equity_direct_growth",
                    "scheme_name": "HDFC Equity Fund Direct Growth",
                    "slug": "hdfc-equity-fund-direct-growth",
                    "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
                },
                {
                    "id": "hdfc_focused_direct_growth",
                    "scheme_name": "HDFC Focused Fund Direct Growth",
                    "slug": "hdfc-focused-fund-direct-growth",
                    "url": "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
                },
                {
                    "id": "hdfc_elss_tax_saver_direct_growth",
                    "scheme_name": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
                    "slug": "hdfc-elss-tax-saver-fund-direct-plan-growth",
                    "url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
                },
                {
                    "id": "hdfc_large_cap_direct_growth",
                    "scheme_name": "HDFC Large Cap Fund Direct Growth",
                    "slug": "hdfc-large-cap-fund-direct-growth",
                    "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                },
            ]
            path = _write_yaml(
                Path(tmp),
                {"version": 1, "amc": "HDFC", "description": "x", "urls": good},
            )
            with self.assertRaises(RegistryError):
                load_registry(path)

    def test_duplicate_url_rejected(self) -> None:
        dup_url = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
        urls = []
        slugs = [
            "hdfc-mid-cap-fund-direct-growth",
            "hdfc-equity-fund-direct-growth",
            "hdfc-focused-fund-direct-growth",
            "hdfc-elss-tax-saver-fund-direct-plan-growth",
            "hdfc-large-cap-fund-direct-growth",
        ]
        for i, slug in enumerate(slugs):
            urls.append(
                {
                    "id": f"id_{i}",
                    "scheme_name": f"Name {i}",
                    "slug": slug,
                    "url": dup_url if i == 4 else f"https://groww.in/mutual-funds/{slug}",
                }
            )
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_yaml(
                Path(tmp),
                {"version": 1, "amc": "HDFC", "description": "x", "urls": urls},
            )
            with self.assertRaises(RegistryError):
                load_registry(path)

    def test_wrong_count_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_yaml(
                Path(tmp),
                {
                    "version": 1,
                    "amc": "HDFC",
                    "description": "x",
                    "urls": [
                        {
                            "id": "only",
                            "scheme_name": "Only",
                            "slug": "hdfc-mid-cap-fund-direct-growth",
                            "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                        }
                    ],
                },
            )
            with self.assertRaises(RegistryError):
                load_registry(path)

    def test_build_registry_roundtrip(self) -> None:
        path = _repo_phases_dir() / "foundations" / "allowlist.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        reg = build_registry(data, allowlist_path=path)
        self.assertEqual(len(reg.schemes), 5)


if __name__ == "__main__":
    unittest.main()
