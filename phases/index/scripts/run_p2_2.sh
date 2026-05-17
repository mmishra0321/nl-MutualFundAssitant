#!/usr/bin/env bash
# Phase 2.2: embed chunks/*.jsonl → embeddings/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
elif [[ -x "${ROOT}/../corpus/.venv/bin/python" ]]; then
  PY="${ROOT}/../corpus/.venv/bin/python"
else
  PY="python3"
fi
exec "$PY" -m ms02_index.p2_2_embeddings "$@"
