# Phase 5 handoff checklist

Use after `./scripts/run_quality_gates.sh` passes locally (or CI **Phase 5 quality** is green).

## Automated gates (`hardening_build.json`)

| Step | Architecture workstream |
|------|-------------------------|
| `validate_allowlist` | Phase 0 — five URLs |
| `corpus_spot_check` | Quality — all schemes normalized |
| `citation_urls` | Quality — allowlisted URLs reachable |
| `retrieval_golden` | Quality — hybrid retrieval |
| `answer_golden` | Quality — E2E answers + citations |
| `red_team` | Quality — refusals / borderline |
| `content_policy_checklist` | Security / policy doc present |
| `api_security` | Security — API PII field handling |
| `log_sanitization` | Security — log redaction |
| `disclaimer_artifacts` | Disclaimer snippet |
| `streamlit_disclaimer` | Streamlit UI — visible disclaimer |
| `frontend_disclaimer` | Legacy static UI — `frontend/index.html` |
| `root_readme` | README deliverable |
| `edge_case_docs` | `docs/edge-cases/` catalogs |
| `success_criteria` | Problem-statement success criteria |

## Manual sign-off

| Item | Owner | Date |
|------|-------|------|
| Spot-checked Streamlit UI (`run_app.sh` or `run_local.sh`) | | |
| Reviewed latest `corpus_build.json` / `index_build.json` dates | | |
| Confirmed no PII fields in API or logs in production config | | |
| GitHub Actions refresh schedule acceptable (10:00 IST) | | |

## Related docs

- [`../../docs/edge-cases/`](../../docs/edge-cases/) — per-phase edge-case catalogs
- [`../foundations/content-policy-checklist.md`](../foundations/content-policy-checklist.md)
- [`../../phased-architecture.md`](../../phased-architecture.md) — Phase 5
