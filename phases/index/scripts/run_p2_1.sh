#!/usr/bin/env bash
# Phase 2.1: chunk normalized/ → chunks/*.jsonl
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CORPUS="$(cd "${ROOT}/../corpus" && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}:${CORPUS}${PYTHONPATH:+:${PYTHONPATH}}"
if [[ -x "${CORPUS}/.venv/bin/python" ]]; then
  PY="${CORPUS}/.venv/bin/python"
elif [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
else
  PY="python3"
fi
exec "$PY" -m ms02_index.p2_1_chunking "$@"
