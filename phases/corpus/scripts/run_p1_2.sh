#!/usr/bin/env bash
# Phase 1.2: fetch allowlisted Groww pages into raw/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
else
  PY="python3"
fi
exec "$PY" -m ms02_corpus.p1_2_fetcher "$@"
