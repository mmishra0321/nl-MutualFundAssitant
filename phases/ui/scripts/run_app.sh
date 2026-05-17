#!/usr/bin/env bash
# Phase 4 — Streamlit UI (needs Phase 2 index built).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
INDEX="${REPO}/phases/index"
VENV="${INDEX}/.venv"
PY="${VENV}/bin/python"
PORT="${STREAMLIT_SERVER_PORT:-8501}"

if [[ ! -x "${PY}" ]]; then
  echo "Run ./scripts/setup_local.sh first." >&2
  exit 1
fi

if [[ ! -f "${INDEX}/index_build.json" ]]; then
  echo "Phase 2 index missing. Run ./scripts/refresh-corpus-index.sh" >&2
  exit 1
fi

# shellcheck source=/dev/null
[[ -f "${REPO}/.env" ]] && set -a && source "${REPO}/.env" && set +a

export MS02_LOCAL_DEV="${MS02_LOCAL_DEV:-1}"
export HF_HOME="${HF_HOME:-${INDEX}/.cache/huggingface}"
export PYTHONPATH="${REPO}/phases/corpus:${REPO}/phases/index:${REPO}/phases/answer_engine${PYTHONPATH:+:${PYTHONPATH}}"

cd "${REPO}"
exec "${PY}" -m streamlit run app.py \
  --server.port "${PORT}" \
  --server.address 127.0.0.1
