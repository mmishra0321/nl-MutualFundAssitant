# Phase 2.3 — Vector store

**Architecture:** `../../../../phased-architecture.md` — Phase 2, subphase 2.3.

## Backend

**Chroma** (persistent local DB under `vector_store/chroma/`). Cosine space; collection `ms02_chunks`.

## Implemented

| Module | Role |
|--------|------|
| `loader.py` | Reads `embeddings/*.jsonl`, validates `source_url` / `scheme_id` against Phase 0 allowlist, loads vectors + metadata into Chroma. Writes `vector_store/manifest.json`. |

## Metadata filters (for 2.4)

Chroma `where` filters on `scheme_id` and `source_url` (and other scalar fields on each chunk).

## Run

Requires Phase **2.2** output.

```bash
cd phases/index
export PYTHONPATH="${PWD}:${PWD}/../corpus"
pip install -r requirements.txt
python -m ms02_index.p2_3_vector_store
```

Or: `./scripts/run_p2_3.sh`
