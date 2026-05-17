# Runbook: local UI + API

## Prerequisites

- Phase 2 index built (`phases/index/index_build.json`)
- Normalized corpus present (`phases/corpus/normalized/`)
- `./scripts/setup_local.sh` completed

## Start

```bash
./scripts/run_local.sh
```

Open http://127.0.0.1:8000/

## Smoke test

Ask: *What is the minimum SIP for HDFC ELSS Tax Saver Direct Plan Growth?*

Expect: factual answer, one Groww URL, last-updated footer when grounded.

## API only

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the expense ratio for HDFC Mid Cap Fund Direct Growth?"}'
```
