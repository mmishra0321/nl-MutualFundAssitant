# Edge Cases — Phase 2: Retrieval Index (RAG Core)

**Scope:** Chunking, embeddings, vector store, retrieval (optional BM25/rerank); metadata must keep `source_url` ∈ allowlist.  
**Architecture ref:** `phased-architecture.md` — Phase 2.

| ID | Scenario | Expected handling | Severity |
|----|----------|-------------------|----------|
| P2-01 | User asks about “HDFC Mid Cap” but chunks from another scheme rank higher due to generic wording (“equity fund”, “SIP”). | Hybrid retrieval (keyword filter on scheme name/slug) or metadata filter `scheme_id` before top-k; test cross-scheme confusion. | High |
| P2-02 | Same numeric fact repeated across overlapping chunks from the same URL. | Deduplicate at display/RAG context stage or tolerate redundancy but ensure single citation URL remains one of five. | Medium |
| P2-03 | Chunking splits a table (expense ratio / exit load) across two chunks so neither is self-contained. | Prefer overlap or table-aware chunking; add regression queries for split-sensitive fields. | Medium |
| P2-04 | Embedding model update changes vectors without corpus text change. | Version embedding model ID in index metadata; full re-embed job; document that retrieval drift is possible across model versions. | Medium |
| P2-05 | Top-k returns zero chunks above similarity threshold. | Surface “insufficient context” to Phase 3; do not widen search to non-allowlisted sources. | High |
| P2-06 | All top-k chunks are from wrong scheme but same AMC (HDFC naming collision). | Strengthen `scheme_id` filtering and query understanding; add evaluation set for each of five schemes. | High |
| P2-07 | Vector DB partial outage or stale collection vs new crawl. | Health check; block queries or return controlled error; never mix old index with new crawl without explicit cutover. | High |
| P2-08 | Optional reranker overfits short queries and drops correct chunk. | Fallback to raw vector top-k if reranker scores are flat; A/B on golden set. | Low |
| P2-09 | `source_url` metadata missing on a chunk (ingestion bug). | Index build should reject or repair; Phase 3 validator must catch before respond. | High |
| P2-10 | Query in Hindi/Hinglish while corpus is English. | Retrieval may miss; Phase 3 should refuse or answer only if retrieved confidence passes threshold—do not hallucinate bilingual facts. | Medium |

**Review trigger:** Change to chunk size, overlap, embedding model, or vector DB schema.
