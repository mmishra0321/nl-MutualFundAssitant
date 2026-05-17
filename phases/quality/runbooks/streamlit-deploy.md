# Runbook: Streamlit Community Cloud deploy

## Prerequisites

- Phase 2 index committed (`phases/index/vector_store/`, `phases/corpus/normalized/`)
- `requirements.txt` at repo root
- `./phases/quality/scripts/run_quality_gates.sh` passes locally

## Deploy steps

1. Push to GitHub (include index artifacts).
2. [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. **Main file:** `app.py` (repo root).
4. **Python:** 3.11.
5. **Secrets:** `GROQ_API_KEY` (optional).

## Post-deploy smoke

Ask: *What is the minimum SIP for HDFC ELSS Tax Saver Direct Plan Growth?*

Expect: factual answer, one Groww URL, last-updated footer when grounded.

Advisory question: no source URL.

## Rollback

Revert Git commit and **Reboot app** in Streamlit Cloud settings.

See also: [`../../docs/deployment/streamlit-deploy-plan.md`](../../docs/deployment/streamlit-deploy-plan.md).
