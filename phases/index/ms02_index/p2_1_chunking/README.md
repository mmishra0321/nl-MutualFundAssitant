# Phase 2.1 — Chunking

**Architecture:** `../../../../phased-architecture.md` — Phase 2, subphase 2.1.

## Implemented

| Module | Role |
|--------|------|
| `chunker.py` | Reads `phases/corpus/normalized/<scheme_id>/page.md` + manifest; **heading-aware** splits on `##`–`####`; **never splits markdown tables** mid-row; trims leading nav / trailing footer chrome; optional **Fund overview** from nav-line fund facts. Writes `phases/index/chunks/<scheme_id>.jsonl` + per-scheme manifest + `chunks/index.json`. |

## Chunk metadata

Each JSONL line includes: `chunk_id`, `scheme_id`, `scheme_name`, `source_url`, `doc_type`, `section_heading`, `text`, `char_count`, `chunk_index`, `raw_fetched_at`, `raw_content_sha256`, `normalized_sha256`, `normalized_at`.

## Run

Requires Phase **1.4** output under `phases/corpus/normalized/`.

```bash
cd phases/index
export PYTHONPATH="${PWD}:${PWD}/../corpus"
python -m ms02_index.p2_1_chunking
# optional: python -m ms02_index.p2_1_chunking /path/to/normalized /path/to/chunks
```

Or: `./scripts/run_p2_1.sh` (sets `PYTHONPATH` for you).
