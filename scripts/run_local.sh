#!/usr/bin/env bash
# Run MS02 on localhost (Streamlit UI + optional REST API). Use before Streamlit Cloud deploy.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${REPO}/phases/index/.venv"
PY="${VENV}/bin/python"
INDEX="${REPO}/phases/index"
UI_APP="${REPO}/phases/ui/scripts/run_app.sh"
UI_API="${REPO}/phases/ui/scripts/run_api.sh"

API_HOST="${MS02_API_HOST:-127.0.0.1}"
API_PORT="${MS02_API_PORT:-8000}"
UI_PORT="${STREAMLIT_SERVER_PORT:-8501}"
SKIP_API="${MS02_SKIP_API:-0}"

API_PID=""

cleanup() {
  [[ -n "${API_PID}" ]] && kill "${API_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ ! -x "${PY}" ]]; then
  echo "Run ./scripts/setup_local.sh first." >&2
  exit 1
fi

if [[ ! -f "${INDEX}/index_build.json" ]]; then
  echo "Phase 2 index missing. Run:" >&2
  echo "  ./scripts/refresh-corpus-index.sh" >&2
  exit 1
fi

# shellcheck source=/dev/null
[[ -f "${REPO}/.env" ]] && set -a && source "${REPO}/.env" && set +a

export MS02_LOCAL_DEV=1
export HF_HOME="${HF_HOME:-${INDEX}/.cache/huggingface}"

echo "==> MS02 local (localhost)"
echo "    Repo: ${REPO}"
echo ""

if [[ "${SKIP_API}" != "1" ]]; then
  echo "==> Starting API  http://${API_HOST}:${API_PORT}/  (docs: /docs)"
  MS02_API_HOST="${API_HOST}" MS02_API_PORT="${API_PORT}" bash "${UI_API}" &
  API_PID=$!
  for _ in $(seq 1 60); do
    if curl -sf "http://${API_HOST}:${API_PORT}/health" >/dev/null 2>&1; then
      echo "    API ready."
      break
    fi
    sleep 0.5
  done
  if ! curl -sf "http://${API_HOST}:${API_PORT}/health" >/dev/null 2>&1; then
    echo "API failed to start. Set MS02_SKIP_API=1 for Streamlit only." >&2
    exit 1
  fi
  echo ""
fi

echo "==> Starting Streamlit UI  http://127.0.0.1:${UI_PORT}/"
echo "    Press Ctrl+C to stop."
echo ""

export STREAMLIT_SERVER_PORT="${UI_PORT}"
export PYTHONPATH="${REPO}/phases/corpus:${REPO}/phases/index:${REPO}/phases/answer_engine${PYTHONPATH:+:${PYTHONPATH}}"
cd "${REPO}"
"${PY}" -m streamlit run app.py \
  --server.port "${UI_PORT}" \
  --server.address 127.0.0.1
