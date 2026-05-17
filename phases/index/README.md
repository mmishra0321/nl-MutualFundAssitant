# Phase 2: Retrieval index (RAG core)

**Architecture:** `../../phased-architecture.md` — Phase 2.

## Folder layout

```text
phases/index/
  README.md
  ms02_index/
    p2_1_chunking/          # ✅ Phase 2.1 — chunking
    p2_2_embeddings/        # ✅ Phase 2.2 — embeddings
    p2_3_vector_store/      # ✅ Phase 2.3 — Chroma vector store
    p2_4_retrieval/         # ✅ Phase 2.4 — hybrid retrieval
    p2_5_pipeline/          # ✅ Phase 2.5 — full index job
    ...
  chunks/                   # 2.1 output: <scheme_id>.jsonl
  embeddings/               # 2.2 output: <scheme_id>.jsonl + manifest.json
  vector_store/             # 2.3 output: chroma/ + manifest.json
  tests/
  requirements.txt          # sentence-transformers (2.2+)
  index_build.json          # 2.5 pipeline manifest (after run)
  scripts/run_p2_1.sh … run_index_build.sh
```

## Phase 2.5 — full index build (recommended)

```bash
cd phases/index
export PYTHONPATH="${PWD}:${PWD}/../corpus"
pip install -r requirements.txt
python -m ms02_index.p2_5_pipeline
# or: ./scripts/run_index_build.sh
# CI: ./scripts/run_index_build.sh --with-tests
```

Runs **2.1 → 2.2 → 2.3 → 2.4** golden checks from `phases/corpus/normalized/`. Writes `index_build.json`.

## Phase 2.4 — run (after 2.3)

```bash
cd phases/index
export PYTHONPATH="${PWD}:${PWD}/../corpus"
python -m ms02_index.p2_4_retrieval --golden
python -m ms02_index.p2_4_retrieval "minimum SIP for HDFC ELSS"
# or: ./scripts/run_p2_4.sh --golden
```

Hybrid **vector + BM25** retrieval; optional `scheme_id` filter when the query names a fund.

## Phase 2.3 — run (after 2.2)

```bash
cd phases/index
export PYTHONPATH="${PWD}:${PWD}/../corpus"
pip install -r requirements.txt
python -m ms02_index.p2_3_vector_store
# or: ./scripts/run_p2_3.sh
```

Loads **98** vectors into **Chroma** at `vector_store/chroma/` (collection `ms02_chunks`). Validates every `source_url` against the Phase 0 allowlist.

## Phase 2.2 — run (after 2.1)

```bash
cd phases/index
export PYTHONPATH="${PWD}"
pip install -r requirements.txt
python -m ms02_index.p2_2_embeddings
# or: ./scripts/run_p2_2.sh
```

Writes `embeddings/<scheme_id>.jsonl` with `embedding` vectors and `embeddings/manifest.json`.

## Phase 2.1 — run

```bash
cd phases/index
export PYTHONPATH="${PWD}:${PWD}/../corpus"
../corpus/.venv/bin/python -m ms02_index.p2_1_chunking
# or: ./scripts/run_p2_1.sh
```

Reads only `phases/corpus/normalized/` (Phase 1 output). Writes `chunks/<scheme_id>.jsonl`.

## Later subphases

| Dir | Subphase | Role |
|-----|----------|------|
| `p2_2_embeddings` | 2.2 | ✅ Done — embed chunks → `embeddings/` |
| `p2_3_vector_store` | 2.3 | ✅ Done — Chroma load from `embeddings/` |
| `p2_4_retrieval` | 2.4 | ✅ Done — top-k + BM25 hybrid |
| `p2_5_pipeline` | 2.5 | ✅ Done — `run_index_build.sh` (2.1→2.4 + golden) |
