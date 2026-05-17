#!/usr/bin/env bash
# Phase 3: answer engine CLI
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INDEX="$(cd "${ROOT}/../index" && pwd)"
CORPUS="$(cd "${ROOT}/../corpus" && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}:${INDEX}:${CORPUS}${PYTHONPATH:+:${PYTHONPATH}}"
if [[ -x "${INDEX}/.venv/bin/python" ]]; then
  PY="${INDEX}/.venv/bin/python"
elif [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
else
  PY="python3"
fi
export HF_HOME="${HF_HOME:-${INDEX}/.cache/huggingface}"
exec "$PY" -m ms02_answer "$@"
