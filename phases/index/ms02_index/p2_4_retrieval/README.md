# Phase 2.4 — Retrieval

**Architecture:** `../../../../phased-architecture.md` — Phase 2, subphase 2.4.

## Implemented

| Module | Role |
|--------|------|
| `retriever.py` | Top-k **vector** search (Chroma + same embedding model as 2.2) + **BM25** hybrid via RRF; optional `scheme_id` filter from query |
| `scheme_resolver.py` | Maps fund names in queries → `scheme_id` |
| `eval.py` | Golden-query evaluation (hybrid vs vector-only) |
| `golden_queries.yaml` | Labeled retrieval golden queries |

## Strategy (for this corpus)

1. **Dense** — Chroma cosine on `all-MiniLM-L6-v2` embeddings  
2. **BM25** — exact terms (expense ratio, exit load, SIP, lock-in, benchmark)  
3. **RRF** — fuse vector + BM25 rankings  
4. **Keyword boost** — light rerank on heading/body term overlap  
5. **`scheme_id` filter** — auto-detected from query when a fund is named  

## Modes

- `hybrid` (default) — RRF + keyword boost
- `vector` — embedding similarity only
- `bm25` — keyword only

## Run

Requires Phase **2.3** Chroma index.

```bash
cd phases/index
export PYTHONPATH="${PWD}:${PWD}/../corpus"
python -m ms02_index.p2_4_retrieval --golden
python -m ms02_index.p2_4_retrieval "minimum SIP for HDFC ELSS"
python -m ms02_index.p2_4_retrieval --mode hybrid --top-k 5 "expense ratio HDFC Mid Cap"
python -m ms02_index.p2_4_retrieval --scheme-id hdfc_elss_tax_saver_direct_growth "lock-in"
```

Or: `./scripts/run_p2_4.sh --golden`
