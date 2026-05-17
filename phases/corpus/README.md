# Phase 1: Corpus pipeline (ingestion)

**Architecture:** `../../phased-architecture.md` — Phase 1.

## Folder layout

```text
phases/corpus/
  README.md                 # this file
  requirements.txt          # PyYAML (Phase 1.1+)
  ms02_corpus/              # Python package — one subfolder per subphase
    __init__.py             # re-exports 1.1 registry API
    p1_1_registry/          # ✅ Phase 1.1 — allowlist load & validation
    p1_2_fetcher/          # ✅ Phase 1.2 — HTTP GET → raw/
    p1_3_extraction/        # ✅ Phase 1.3 — HTML cleanup → intermediate/
    p1_4_normalization/     # ✅ Phase 1.4 — Markdown → normalized/
    p1_5_pipeline/        # ✅ Phase 1.5 — orchestration: validate.sh + 1.1–1.4
  tests/                    # unittest (e.g. test_p1_1_registry.py)
  scripts/                  # run_ingestion.sh (1.5), run_p1_1.sh … run_p1_4.sh
  raw/                      # 1.2 output (snapshots)
  intermediate/             # 1.3 optional staging
  normalized/               # 1.4 output
  corpus_build.json         # 1.5 pipeline manifest (after run)
```

## Phase 1.5 — full pipeline (1.1–1.4)

Runs `validate_allowlist.sh`, then registry → fetch → extract → normalize.

```bash
cd phases/corpus
export PYTHONPATH="${PWD}"
./scripts/run_ingestion.sh
# optional: ./scripts/run_ingestion.sh --with-tests
# optional: ./scripts/run_ingestion.sh --skip-validate-sh
```

See `ms02_corpus/p1_5_pipeline/README.md`.

## Phase 1.4 — run (after 1.2 + 1.3)

```bash
cd phases/corpus
export PYTHONPATH="${PWD}"
pip install -r requirements.txt
python -m ms02_corpus.p1_4_normalization
# or: ./scripts/run_p1_4.sh
```

Writes `normalized/<scheme_id>/page.md`. Exits non-zero on any failure.

## Phase 1.3 — run (after 1.2)

```bash
cd phases/corpus
export PYTHONPATH="${PWD}"
pip install -r requirements.txt
python -m ms02_corpus.p1_3_extraction
# or: ./scripts/run_p1_3.sh
```

Writes `intermediate/<scheme_id>/extracted.html`. Exits non-zero if any scheme fails.

## Phase 1.2 — run (network)

```bash
cd phases/corpus
export PYTHONPATH="${PWD}"
pip install -r requirements.txt
python -m ms02_corpus.p1_2_fetcher
# or: ./scripts/run_p1_2.sh
```

Writes under `raw/<scheme_id>/` (see `ms02_corpus/p1_2_fetcher/README.md`). Exits non-zero if any fetch fails.

## Phase 1.1 — run

From `phases/corpus` (set `PYTHONPATH` to this directory so `ms02_corpus` resolves):

```bash
cd phases/corpus
python3 -m venv .venv && source .venv/bin/activate   # first time only
pip install -r requirements.txt
export PYTHONPATH="${PWD}"
python -m unittest discover -s tests -v
python -m ms02_corpus.p1_1_registry
```

Or use the helper script (same `PYTHONPATH` + prefers `.venv`):

```bash
cd phases/corpus
chmod +x scripts/run_p1_1.sh   # once
./scripts/run_p1_1.sh
```

**Programmatic use**

```python
from pathlib import Path
from ms02_corpus import load_registry

reg = load_registry()
# or load_registry(Path("/path/to/allowlist.yaml"))
```

## Later subphases

| Dir | Subphase | Role |
|-----|----------|------|
| `p1_2_fetcher` | 1.2 | ✅ Done — fetch allowlisted URLs → `raw/` |
| `p1_3_extraction` | 1.3 | ✅ Done — strip scripts/chrome → `intermediate/` |
| `p1_4_normalization` | 1.4 | ✅ Done — Markdown + manifest → `normalized/` |
| `p1_5_pipeline` | 1.5 | ✅ Done — `run_ingestion.sh` / `python -m ms02_corpus.p1_5_pipeline` |

## Exit criteria (Phase 1 overall)

- All **five** URLs ingest on demand (after 1.2–1.5).
- Re-crawl uses the same closed allowlist (1.1 + `../foundations/validate_allowlist.sh`).
