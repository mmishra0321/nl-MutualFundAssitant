# Phase 1.5 — Full corpus pipeline

**Architecture:** `../../../../phased-architecture.md` — Phase 1, subphase 1.5.

## Implemented

| Module | Role |
|--------|------|
| `pipeline.py` | Runs **`phases/foundations/validate_allowlist.sh`**, then **`load_registry()` (1.1)** → **`fetch_all` (1.2)** → **`extract_all` (1.3)** → **`normalize_all` (1.4)**. Stops on first failing subphase. Re-runs are **idempotent** (overwrite `raw/`, `intermediate/`, `normalized/`). Optional **`--with-tests`**: `python -m unittest discover -s tests`. |

## CLI

```bash
cd phases/corpus
export PYTHONPATH="${PWD}"
pip install -r requirements.txt

# Full pipeline (shell allowlist check + fetch needs network)
python -m ms02_corpus.p1_5_pipeline

# CI-style: run unit tests first, then ingest
python -m ms02_corpus.p1_5_pipeline --with-tests

# Skip shell check (e.g. Windows without bash — not recommended)
python -m ms02_corpus.p1_5_pipeline --skip-validate-sh

# Custom roots (same order as subcommands 1.2–1.4)
python -m ms02_corpus.p1_5_pipeline [--flags] /path/raw /path/intermediate /path/normalized
```

Or: **`./scripts/run_ingestion.sh`** (same args).

Exit **0** only if every step succeeds; JSON summary on stdout. Writes **`phases/corpus/corpus_build.json`** with per-step results and postflight checks (`page.md` + allowlisted `source_url` per scheme).
