#!/usr/bin/env bash
# Phase 1.3: extract main HTML from raw/ → intermediate/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
else
  PY="python3"
fi
exec "$PY" -m ms02_corpus.p1_3_extraction "$@"
