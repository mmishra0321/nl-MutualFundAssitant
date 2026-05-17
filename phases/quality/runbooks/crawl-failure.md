# Runbook: Corpus crawl failure

## Symptoms

- `refresh-corpus-index` GitHub Action fails at **Phase 1.5**
- `corpus_build.json` shows `ok: false` or HTTP ≠ 200 for a scheme
- UI answers cite stale `raw_fetched_at` dates

## Checks

1. Run allowlist validation:
   ```bash
   bash phases/foundations/validate_allowlist.sh
   ```
2. Re-run corpus only:
   ```bash
   cd phases/corpus && python -m ms02_corpus.p1_5_pipeline
   ```
3. Inspect per-scheme manifest under `phases/corpus/raw/<scheme_id>/manifest.json`.

## Common causes

| Cause | Mitigation |
|-------|------------|
| Groww rate limit / 403 | Wait and re-run; avoid parallel crawls |
| HTML layout change | Update extractor in `p1_3_extraction` |
| Network timeout | Increase fetch timeout in `p1_2_fetcher` |

## Recovery

```bash
./scripts/refresh-corpus-index.sh
./phases/quality/scripts/run_quality_gates.sh
```

Do not deploy UI changes until Phase 1.5 and 2.5 both report `"ok": true`.
