"""Tests for Phase 3 answer engine."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ms02_answer.gate import (
    Route,
    classify_query,
    contains_pii,
    is_advisory,
    is_scheme_only_query,
    mentions_unknown_fund_name,
)
from ms02_answer.generator import (
    build_factual_answer,
    detect_fact_intent,
    has_sufficient_grounding,
)
from ms02_answer.models import AnswerResult
from ms02_answer.validator import validate_result
from ms02_index.p2_4_retrieval.retriever import RetrievalHit


class TestGate(unittest.TestCase):
    def test_pii_pan(self) -> None:
        self.assertTrue(contains_pii("My PAN is ABCDE1234F"))

    def test_advisory(self) -> None:
        self.assertTrue(is_advisory("Should I invest in HDFC Mid Cap?"))

    def test_factual_route(self) -> None:
        self.assertEqual(
            classify_query("What is the minimum SIP for HDFC ELSS?"),
            Route.FACTUAL,
        )

    def test_unknown_fund_out_of_scope(self) -> None:
        names = ("HDFC ELSS Tax Saver Fund Direct Plan Growth",)
        self.assertTrue(
            mentions_unknown_fund_name("nextleaf fund", known_scheme_names=names)
        )
        self.assertEqual(
            classify_query("nextleaf fund", known_scheme_names=names),
            Route.REFUSAL_OUT_OF_SCOPE,
        )

    def test_generic_fact_question_stays_factual(self) -> None:
        names = ("HDFC ELSS Tax Saver Fund Direct Plan Growth",)
        self.assertFalse(
            mentions_unknown_fund_name(
                "What is the minimum SIP for HDFC ELSS?",
                known_scheme_names=names,
            )
        )

    def test_scheme_name_only_is_insufficient(self) -> None:
        names = (
            "HDFC Mid Cap Fund Direct Growth",
            "HDFC ELSS Tax Saver Fund Direct Plan Growth",
        )
        self.assertTrue(
            is_scheme_only_query("hdfc mid cap", known_scheme_names=names)
        )
        self.assertEqual(
            classify_query("hdfc mid cap", known_scheme_names=names),
            Route.INSUFFICIENT,
        )
        self.assertEqual(
            classify_query(
                "What is the exit load for HDFC Mid Cap?",
                known_scheme_names=names,
            ),
            Route.FACTUAL,
        )


class TestGrounding(unittest.TestCase):
    def test_nav_query_returns_nav_only(self) -> None:
        blob = (
            "NAV: 15 May '26₹1,175.45Min. for SIP₹100Fund size (AUM)₹38,121.27 Cr"
            "Expense ratio0.99%"
        )
        hit = RetrievalHit(
            chunk_id="c1",
            scheme_id="hdfc_large_cap_direct_growth",
            scheme_name="HDFC Large Cap Fund Direct Growth",
            source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            section_heading="Fund overview",
            text=blob,
            score=0.9,
        )
        q = "what is NAV for HDFC large cap mutual fund"
        self.assertEqual(detect_fact_intent(q), "nav")
        ans = build_factual_answer(q, [hit])
        self.assertIn("NAV", ans)
        self.assertIn("1,175.45", ans)
        self.assertNotIn("SIP", ans)
        self.assertNotIn("Expense ratio", ans)
        self.assertNotIn("AUM", ans)

    def test_expense_ratio_only(self) -> None:
        hit = RetrievalHit(
            chunk_id="c1",
            scheme_id="hdfc_large_cap_direct_growth",
            scheme_name="HDFC Large Cap Fund Direct Growth",
            source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            section_heading="Fund overview",
            text="Expense ratio0.99% Min. for SIP₹100 NAV: 15 May '26₹1,175.45",
            score=0.9,
        )
        ans = build_factual_answer("expense ratio HDFC large cap", [hit])
        self.assertIn("0.99%", ans)
        self.assertNotIn("SIP", ans)
        self.assertNotIn("NAV", ans)

    def test_no_grounding_for_unrelated_fund_token(self) -> None:
        hit = RetrievalHit(
            chunk_id="c1",
            scheme_id="hdfc_large_cap_direct_growth",
            scheme_name="HDFC Large Cap Fund Direct Growth",
            source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            section_heading="Overview",
            text="Min. for SIP₹100 Fund size (AUM)₹26,182 Expense ratio0.76%",
            score=0.9,
        )
        self.assertFalse(
            has_sufficient_grounding("nextleaf fund", [hit]),
        )


class TestValidator(unittest.TestCase):
    def test_factual_needs_url(self) -> None:
        url = "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth"
        r = AnswerResult(
            question="q",
            answer="The expense ratio is 0.9%.",
            source_url=url,
            last_updated="2026-05-15",
            route="factual",
        )
        ok, _ = validate_result(r, allowed_urls=frozenset([url]))
        self.assertTrue(ok)

    def test_refusal_no_url(self) -> None:
        r = AnswerResult(
            question="q",
            answer="I cannot advise.",
            source_url=None,
            last_updated=None,
            route="refusal_advisory",
        )
        ok, _ = validate_result(r, allowed_urls=frozenset())
        self.assertTrue(ok)

    def test_refusal_rejects_url(self) -> None:
        r = AnswerResult(
            question="q",
            answer="No.",
            source_url="https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
            last_updated=None,
            route="refusal_pii",
        )
        ok, err = validate_result(
            r,
            allowed_urls=frozenset(
                ["https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth"]
            ),
        )
        self.assertFalse(ok)
        self.assertIn("must not", err or "")


class TestEngineGroq(unittest.TestCase):
    @patch("ms02_answer.engine.groq_generate_answer")
    @patch("ms02_answer.engine.Retriever")
    def test_factual_path_calls_groq_when_enabled(
        self, mock_retriever: MagicMock, mock_groq: MagicMock
    ) -> None:
        from ms02_answer.engine import AnswerEngine
        from ms02_index.p2_4_retrieval.retriever import RetrievalHit

        hit = RetrievalHit(
            chunk_id="c1",
            scheme_id="hdfc_large_cap_direct_growth",
            scheme_name="HDFC Large Cap Fund Direct Growth",
            source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            section_heading="Overview",
            text="NAV: 15 May '26₹1,175.45 Expense ratio0.99%",
            score=0.9,
        )
        mock_retriever.return_value.hybrid_search.return_value = [hit]
        mock_groq.return_value = "The NAV is ₹1,175.45 as of 15 May 2026."

        engine = AnswerEngine(use_groq=True)
        res = engine.ask("What is the NAV for HDFC Large Cap Fund Direct Growth?")

        mock_groq.assert_called_once()
        self.assertEqual(res.route, "factual")
        self.assertIn("1,175.45", res.answer)
        self.assertIsNotNone(res.source_url)


class TestEngineMocked(unittest.TestCase):
    @patch("ms02_answer.engine.Retriever")
    def test_pii_no_url(self, mock_cls: MagicMock) -> None:
        from ms02_answer.engine import AnswerEngine

        engine = AnswerEngine()
        res = engine.ask("My PAN is ABCDE1234F please check my folio")
        self.assertEqual(res.route, Route.REFUSAL_PII.value)
        self.assertIsNone(res.source_url)
        mock_cls.return_value.hybrid_search.assert_not_called()

    @patch("ms02_answer.engine.Retriever")
    def test_scheme_name_only_no_url(self, mock_cls: MagicMock) -> None:
        from ms02_answer.engine import AnswerEngine

        engine = AnswerEngine()
        res = engine.ask("hdfc mid cap")
        self.assertEqual(res.route, Route.INSUFFICIENT.value)
        self.assertIsNone(res.source_url)
        self.assertIn("specific factual question", res.answer.lower())
        mock_cls.return_value.hybrid_search.assert_not_called()

    @patch("ms02_answer.engine.Retriever")
    def test_unknown_fund_no_url(self, mock_cls: MagicMock) -> None:
        from ms02_answer.engine import AnswerEngine

        engine = AnswerEngine()
        res = engine.ask("nextleaf fund")
        self.assertEqual(res.route, Route.REFUSAL_OUT_OF_SCOPE.value)
        self.assertIsNone(res.source_url)
        self.assertIn("do not have an answer", res.answer.lower())
        mock_cls.return_value.hybrid_search.assert_not_called()

    @patch("ms02_answer.engine.Retriever")
    def test_insufficient_no_url(self, mock_cls: MagicMock) -> None:
        from ms02_answer.engine import AnswerEngine

        mock_cls.return_value.hybrid_search.return_value = []
        engine = AnswerEngine()
        res = engine.ask("What is the minimum SIP for HDFC ELSS?")
        self.assertEqual(res.route, Route.INSUFFICIENT.value)
        self.assertIsNone(res.source_url)


if __name__ == "__main__":
    unittest.main()
