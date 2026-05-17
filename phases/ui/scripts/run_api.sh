#!/usr/bin/env bash
# Optional REST API for local dev / integrations (POST /api/ask, GET /health).
# Streamlit UI uses the answer engine in-process; start both via ./scripts/run_local.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../backend" && pwd)"
PHASES="$(cd "${ROOT}/../.." && pwd)"
INDEX="$(cd "${PHASES}/index" && pwd)"
CORPUS="$(cd "${PHASES}/corpus" && pwd)"
P3="$(cd "${PHASES}/answer_engine" && pwd)"
cd "${ROOT}"

export PYTHONPATH="${ROOT}:${P3}:${INDEX}:${CORPUS}${PYTHONPATH:+:${PYTHONPATH}}"
export HF_HOME="${HF_HOME:-${INDEX}/.cache/huggingface}"

if [[ -x "${INDEX}/.venv/bin/python" ]]; then PY="${INDEX}/.venv/bin/python"
elif [[ -x "${ROOT}/.venv/bin/python" ]]; then PY="${ROOT}/.venv/bin/python"
else PY="${PYTHON:-python3}"; fi

HOST="${MS02_API_HOST:-127.0.0.1}"
PORT="${MS02_API_PORT:-8000}"
exec "${PY}" -m uvicorn main:app --host "${HOST}" --port "${PORT}" "$@"
