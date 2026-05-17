"""Tests for Phase 5 policy and handoff checks."""

from __future__ import annotations

import unittest
from pathlib import Path

from ms02_hardening.checks.handoff import check_edge_case_docs
from ms02_hardening.checks.policy import (
    check_allowlist_five_urls,
    check_content_policy_checklist,
)
from ms02_hardening.checks.success_criteria import evaluate_success_criteria

PHASES = Path(__file__).resolve().parents[2]
REPO = PHASES.parent


class TestPolicyAndHandoff(unittest.TestCase):
    def test_content_policy_checklist(self) -> None:
        r = check_content_policy_checklist(PHASES)
        self.assertTrue(r["ok"], r)

    def test_allowlist_five(self) -> None:
        r = check_allowlist_five_urls(PHASES)
        self.assertTrue(r["ok"], r)

    def test_edge_case_docs(self) -> None:
        r = check_edge_case_docs(REPO)
        self.assertTrue(r["ok"], r)

    def test_success_criteria_all_pass(self) -> None:
        steps = {
            "retrieval_golden": True,
            "corpus_spot_check": True,
            "red_team": True,
            "answer_golden": True,
            "citation_urls": True,
            "streamlit_disclaimer": True,
            "frontend_disclaimer": True,
            "disclaimer_artifacts": True,
            "root_readme": True,
            "log_sanitization": True,
            "api_security": True,
        }
        r = evaluate_success_criteria(step_results=steps, repo_root=REPO)
        self.assertTrue(r["ok"], r)


if __name__ == "__main__":
    unittest.main()
