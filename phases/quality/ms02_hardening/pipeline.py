"""
Phase 5 — Hardening pipeline (quality gates + handoff checks).

Runs corpus spot-check, citation reachability, retrieval golden, answer golden,
red-team evaluation, disclaimer/README handoff checks.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ms02_answer.engine import AnswerEngine
from ms02_hardening.checks.answers import (
    run_answer_golden_evaluation,
    run_red_team,
    run_retrieval_golden,
)
from ms02_hardening.checks.citations import check_citation_urls
from ms02_hardening.checks.corpus import check_corpus_spot, default_normalized_root
from ms02_hardening.checks.api_security import run_api_security_tests
from ms02_hardening.checks.handoff import (
    check_disclaimer_artifacts,
    check_edge_case_docs,
    check_root_readme,
    check_frontend_disclaimer,
    check_streamlit_disclaimer,
)
from ms02_hardening.checks.policy import (
    check_allowlist_five_urls,
    check_content_policy_checklist,
)
from ms02_hardening.checks.success_criteria import evaluate_success_criteria
from ms02_hardening.logging_policy import sanitize_for_log


class PipelineError(RuntimeError):
    pass


@dataclass
class StepResult:
    step: str
    ok: bool
    detail: dict[str, Any]


def _phases_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    return _phases_root().parent


def _hardening_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_validate_allowlist_sh() -> str:
    script = _phases_root() / "foundations" / "validate_allowlist.sh"
    if not script.is_file():
        raise PipelineError(f"Missing {script}")
    proc = subprocess.run(
        ["bash", str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise PipelineError(proc.stderr or proc.stdout or "validate_allowlist.sh failed")
    return (proc.stdout or "").strip() or "allowlist OK"


def run_phase5_pipeline(
    *,
    phases_root: Path | None = None,
    skip_network: bool = False,
    skip_answer_golden: bool = False,
    use_groq: bool = False,
) -> dict[str, Any]:
    phases = phases_root or _phases_root()
    repo = phases.parent
    hardening = _hardening_root()
    allowlist = phases / "foundations" / "allowlist.yaml"
    normalized = default_normalized_root(phases)

    os.environ.setdefault(
        "HF_HOME",
        str(phases / "index" / ".cache" / "huggingface"),
    )

    steps: list[StepResult] = []

    try:
        msg = run_validate_allowlist_sh()
        steps.append(StepResult("validate_allowlist", True, {"message": msg}))
    except PipelineError as exc:
        steps.append(StepResult("validate_allowlist", False, {"error": str(exc)}))
        return _finalize(steps, phases, repo)

    corpus = check_corpus_spot(
        normalized_root=normalized,
        allowlist_path=allowlist,
    )
    steps.append(StepResult("corpus_spot_check", corpus["ok"], corpus))

    citations = check_citation_urls(allowlist, skip_network=skip_network)
    steps.append(StepResult("citation_urls", citations["ok"], citations))

    try:
        retrieval = run_retrieval_golden()
        steps.append(StepResult("retrieval_golden", retrieval.get("ok", False), retrieval))
    except Exception as exc:
        steps.append(
            StepResult("retrieval_golden", False, {"error": str(exc)}),
        )

    engine: AnswerEngine | None = None
    if not skip_answer_golden:
        try:
            engine = AnswerEngine(use_groq=use_groq)
        except Exception as exc:
            steps.append(
                StepResult(
                    "answer_engine_start",
                    False,
                    {"error": str(exc)},
                ),
            )
            skip_answer_golden = True

    if not skip_answer_golden and engine is not None:
        answer_golden = run_answer_golden_evaluation(engine)
        steps.append(
            StepResult("answer_golden", answer_golden["ok"], answer_golden),
        )
        red_team = run_red_team(engine)
        steps.append(StepResult("red_team", red_team["ok"], red_team))
    else:
        steps.append(
            StepResult("answer_golden", False, {"skipped": True}),
        )
        steps.append(StepResult("red_team", False, {"skipped": True}))

    policy = check_content_policy_checklist(phases)
    steps.append(StepResult("content_policy_checklist", policy["ok"], policy))

    allowlist = check_allowlist_five_urls(phases)
    steps.append(StepResult("allowlist_five_urls", allowlist["ok"], allowlist))

    edge_docs = check_edge_case_docs(repo)
    steps.append(StepResult("edge_case_docs", edge_docs["ok"], edge_docs))

    disclaimer = check_disclaimer_artifacts(hardening)
    steps.append(StepResult("disclaimer_artifacts", disclaimer["ok"], disclaimer))

    ui_st = check_streamlit_disclaimer(phases)
    steps.append(StepResult("streamlit_disclaimer", ui_st["ok"], ui_st))
    ui_fe = check_frontend_disclaimer(phases)
    steps.append(StepResult("frontend_disclaimer", ui_fe["ok"], ui_fe))

    readme = check_root_readme(repo)
    steps.append(StepResult("root_readme", readme["ok"], readme))

    api_sec = run_api_security_tests(phases)
    steps.append(StepResult("api_security", api_sec["ok"], api_sec))

    # Security self-check: log sanitizer must redact sample PII
    sample = "Contact user@mail.com PAN ABCDE1234F"
    sanitized = sanitize_for_log(sample)
    sec_ok = "[REDACTED]" in sanitized and "user@mail.com" not in sanitized
    steps.append(
        StepResult(
            "log_sanitization",
            sec_ok,
            {"sample_in": sample, "sample_out": sanitized},
        ),
    )

    step_ok = {s.step: s.ok for s in steps}
    success = evaluate_success_criteria(step_results=step_ok, repo_root=repo)
    steps.append(StepResult("success_criteria", success["ok"], success))

    return _finalize(steps, phases, repo)


def _finalize(
    steps: list[StepResult],
    phases: Path,
    repo: Path,
) -> dict[str, Any]:
    ok = all(s.ok for s in steps)
    manifest = {
        "ok": ok,
        "phases_root": str(phases.resolve()),
        "repo_root": str(repo.resolve()),
        "manifest_path": str((_hardening_root() / "hardening_build.json").resolve()),
        "steps": [
            {"step": s.step, "ok": s.ok, "detail": s.detail} for s in steps
        ],
    }
    out = _hardening_root() / "hardening_build.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Phase 5 — hardening pipeline.")
    p.add_argument(
        "--skip-network",
        action="store_true",
        help="Skip live HTTP checks for allowlisted URLs.",
    )
    p.add_argument(
        "--skip-answer-golden",
        action="store_true",
        help="Skip E2E answer golden + red-team (no index required).",
    )
    p.add_argument(
        "--use-groq",
        action="store_true",
        help="Use Groq for answer golden (default: extractive-only).",
    )
    p.add_argument("--json", action="store_true", help="Print JSON manifest only.")
    args = p.parse_args(list(argv) if argv is not None else None)

    report = run_phase5_pipeline(
        skip_network=args.skip_network,
        skip_answer_golden=args.skip_answer_golden,
        use_groq=args.use_groq,
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for step in report["steps"]:
            mark = "OK" if step["ok"] else "FAIL"
            print(f"[{mark}] {step['step']}")
        print()
        print(json.dumps({"ok": report["ok"]}, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
