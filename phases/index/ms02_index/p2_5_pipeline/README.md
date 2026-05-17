# Phase 2.5 — Index job & exit criteria

**Architecture:** `../../../../phased-architecture.md` — Phase 2, subphase 2.5.

## Pipeline order

1. `validate_allowlist.sh` (unless `--skip-validate-sh`)
2. Optional `unittest discover` (`--with-tests`)
3. **2.0** registry (5 schemes) + normalized preflight
4. **2.1** chunk `normalized/` → `chunks/` + **chunk metadata** allowlist check
5. **2.2** embed chunks → `embeddings/`
6. **2.3** load Chroma → `vector_store/chroma/`
7. **2.4** golden-query eval + smoke (non-zero hits per golden query)
8. **2.5_exit** — final pass/fail summary

Writes `phases/index/index_build.json` with step results.

## Run

Requires Phase **1** `normalized/` for all five schemes.

```bash
cd phases/index
export PYTHONPATH="${PWD}:${PWD}/../corpus"
pip install -r requirements.txt
python -m ms02_index.p2_5_pipeline
# or: ./scripts/run_index_build.sh
```

CI: add `--with-tests` to run unit tests before indexing.
