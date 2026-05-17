# UI — Streamlit app

Facts-only HDFC mutual fund FAQ. Calls `ms02_answer.AnswerEngine` in-process.

## Run on localhost

From repo root:

```bash
./scripts/setup_local.sh          # once
./scripts/refresh-corpus-index.sh # if index not built
./scripts/run_local.sh            # Streamlit :8501 + API :8000
```

Or Streamlit only:

```bash
./phases/ui/scripts/run_app.sh    # http://127.0.0.1:8501/
```

**Prereq:** Phase 2 index built (`../index/index_build.json` exists).

## Deploy (Streamlit Cloud)

- **Main file:** `app.py` (repo root)
- **Requirements:** `requirements.txt`
- **Secrets:** `GROQ_API_KEY` (optional) — see `.streamlit/secrets.toml.example`

See `phases/quality/runbooks/streamlit-deploy.md` and `docs/deployment/streamlit-deploy-plan.md`.

## Optional REST API + static UI

```bash
./phases/ui/scripts/run_api.sh    # port 8000 — POST /api/ask, static UI at /
```

Legacy static HTML: `frontend/`.
