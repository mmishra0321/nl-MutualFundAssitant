# Quality gates (Phase 5)

**Architecture:** `../../phased-architecture.md` — Phase 5.

End-to-end checks before handoff: corpus completeness, citation URLs, retrieval/answer golden tests, red-team replay, disclaimer and README presence.

## Run

```bash
# Full pipeline (needs built index under ../index/)
./scripts/run_quality_gates.sh

./scripts/run_quality_gates.sh --skip-network
./scripts/run_quality_gates.sh --skip-answer-golden
```

Output: `hardening_build.json`.

## Layout

| Path | Role |
|------|------|
| `ms02_hardening/pipeline.py` | Orchestrator (`python -m ms02_hardening`) |
| `golden_tests/answer_golden.yaml` | E2E answer expectations |
| `disclaimer/` | Reusable disclaimer text + HTML |
| `runbooks/` | Crawl failure, Actions alerts, Streamlit deploy |
| `scripts/run_quality_gates.sh` | Local launcher |
| `HANDOFF.md` | Manual sign-off after automated gates pass |

## Related

- `../foundations/red-team-queries.yaml`
- `../index/ms02_index/p2_4_retrieval/golden_queries.yaml`
- `../../docs/edge-cases/` — written edge-case catalogs per phase
- `../foundations/content-policy-checklist.md`
