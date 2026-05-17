#!/usr/bin/env bash
# Phase 1.5: full corpus pipeline (validate.sh → 1.1 → 1.2 → 1.3 → 1.4)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
else
  PY="python3"
fi
exec "$PY" -m ms02_corpus.p1_5_pipeline "$@"
