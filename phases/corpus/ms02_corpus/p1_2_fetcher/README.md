# Phase 1.2 — Raw fetcher

**Architecture:** `../../../../phased-architecture.md` — Phase 1, subphase 1.2.

## Implemented

| Module | Role |
|--------|------|
| `fetcher.py` | `fetch_all()`, `fetch_scheme_raw()` — `GET` only each `Registry` URL; `User-Agent` + timeout; retries on 408/429/5xx; **no** PDF responses; post-redirect URL must match that scheme’s allowlisted URL on `groww.in`. |
| `__main__.py` | CLI: `python -m ms02_corpus.p1_2_fetcher` [optional `raw_dir`]. |

## Output layout

```text
raw/<scheme_id>/latest.html    # bytes from HTTP body on success
raw/<scheme_id>/manifest.json  # ok, hashes, timestamps, errors
```

## Run

From `phases/corpus` with `PYTHONPATH=$PWD` and deps installed:

```bash
pip install -r requirements.txt
export PYTHONPATH="${PWD}"
python -m ms02_corpus.p1_2_fetcher
# or custom output root:
python -m ms02_corpus.p1_2_fetcher /path/to/raw
```

Or: `./scripts/run_p1_2.sh` (uses `.venv` if present).

**Note:** Requires network access to `groww.in`. Respectful `delay_between_schemes_s` (default 0.75s) between requests.
