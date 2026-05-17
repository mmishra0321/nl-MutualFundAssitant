# Phase 1.4 — Normalization

**Architecture:** `../../../../phased-architecture.md` — Phase 1, subphase 1.4.

## Implemented

| Module | Role |
|--------|------|
| `normalizer.py` | Reads `intermediate/<scheme_id>/extracted.html` + `manifest.json`, checks `ok`, verifies **`extracted_sha256`** matches disk, checks **`source_url`** ∈ Phase 0 allowlist and matches the registry row, re-hashes **`raw/<scheme_id>/latest.html`** and requires it equals **`raw_content_sha256`** (provenance aligned with stored raw snapshot). Converts HTML → **Markdown** via **markdownify** (no HTTP). Writes **`normalized/<scheme_id>/page.md`** + **`manifest.json`** (`doc_type`: `groww_scheme_page`, `normalized_sha256`, timestamps). |

## Output

```text
normalized/<scheme_id>/page.md
normalized/<scheme_id>/manifest.json
```

## Run

Requires **1.2** raw + **1.3** intermediate for all schemes.

```bash
cd phases/corpus
export PYTHONPATH="${PWD}"
pip install -r requirements.txt
python -m ms02_corpus.p1_4_normalization
# optional: python -m ms02_corpus.p1_4_normalization /path/intermediate /path/normalized /path/raw
```

Or: `./scripts/run_p1_4.sh`
