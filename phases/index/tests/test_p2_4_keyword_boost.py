"""Tests for Phase 2.4 keyword boost."""

from __future__ import annotations

import unittest

from ms02_index.p2_4_retrieval.keyword_boost import (
    apply_keyword_boost,
    keyword_boost_score,
)


class TestKeywordBoost(unittest.TestCase):
    def test_boost_higher_for_matching_heading(self) -> None:
        low = keyword_boost_score(
            "minimum SIP",
            {"section_heading": "Other", "text": "generic fund text"},
        )
        high = keyword_boost_score(
            "minimum SIP",
            {
                "section_heading": "### Minimum investments",
                "text": "Min. for SIP ₹500",
            },
        )
        self.assertGreater(high, low)

    def test_apply_reorders(self) -> None:
        meta = {
            "a": {"section_heading": "Foo", "text": "bar"},
            "b": {
                "section_heading": "### Minimum investments",
                "text": "Min. for SIP ₹500",
            },
        }
        ordered = apply_keyword_boost(
            [("a", 1.0), ("b", 0.9)],
            query="minimum SIP",
            meta_by_id=meta,
        )
        self.assertEqual(ordered[0][0], "b")


if __name__ == "__main__":
    unittest.main()
