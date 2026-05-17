# MS02 — project layout

Each folder below is one layer of the RAG stack. Python packages (`ms02_*`) live inside the layer that owns them.

| Folder | Purpose |
|--------|---------|
| [`foundations/`](foundations/) | Allowlist (5 Groww URLs), compliance checklist |
| [`corpus/`](corpus/) | Ingestion: `raw/` → `intermediate/` → `normalized/page.md` |
| [`index/`](index/) | Chunking, embeddings, Chroma vector store |
| [`answer_engine/`](answer_engine/) | Query gate, retrieval, Groq RAG, response validation |
| [`ui/`](ui/) | Streamlit app (+ optional REST API under `ui/backend/`) |
| [`quality/`](quality/) | Golden tests, runbooks, disclaimer snippets, CI quality pipeline |

**Path constants:** [`ms02_paths.py`](ms02_paths.py) — use in new code instead of hard-coded folder names.

## Common commands

```bash
# Full refresh (ingest + index)
../../scripts/refresh-corpus-index.sh

# Per layer
./corpus/scripts/run_ingestion.sh
./index/scripts/run_index_build.sh
./quality/scripts/run_quality_gates.sh
./ui/scripts/run_app.sh
```

**Allowlist:** `foundations/allowlist.yaml` (exactly five scheme URLs).
