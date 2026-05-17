# Phase 2.2 — Embeddings

**Architecture:** `../../../../phased-architecture.md` — Phase 2, subphase 2.2.

## Implemented

| Module | Role |
|--------|------|
| `embedder.py` | Loads `chunks/<scheme_id>.jsonl`, skips tiny/boilerplate chunks, batch-embeds with **sentence-transformers** (`all-MiniLM-L6-v2` default, 384-dim, L2-normalized). Writes `embeddings/<scheme_id>.jsonl` (chunk fields + `embedding` array) and `embeddings/manifest.json` (`embedding_model_id`, `embedding_dimensions`, corpus fingerprint). |

## Input text format

`{scheme_name} | {section_heading}\n{text}`

## Run

Requires Phase **2.1** output under `chunks/`.

```bash
cd phases/index
python3 -m venv .venv && source .venv/bin/activate   # first time
pip install -r requirements.txt
export PYTHONPATH="${PWD}"
python -m ms02_index.p2_2_embeddings
```

Or: `./scripts/run_p2_2.sh` (uses `index/.venv` or `corpus/.venv`).

First run downloads the model from Hugging Face (~90MB).
