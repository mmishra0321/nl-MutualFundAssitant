#!/usr/bin/env bash
# One-time local setup: venv + Python deps for localhost (Streamlit + optional API).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${REPO}/phases/index/.venv"
PY="${VENV}/bin/python"

echo "==> MS02 local setup"
echo "    Repo: ${REPO}"

if [[ ! -x "${PY}" ]]; then
  echo "==> Creating venv at phases/index/.venv"
  python3 -m venv "${VENV}"
fi

"${PY}" -m pip install --upgrade pip
"${PY}" -m pip install -r "${REPO}/requirements.txt"
"${PY}" -m pip install -r "${REPO}/phases/ui/backend/requirements.txt"

if [[ ! -f "${REPO}/.env" ]]; then
  cp "${REPO}/.env.example" "${REPO}/.env"
  echo "==> Created .env from .env.example (add GROQ_API_KEY if desired)"
fi

INDEX_MANIFEST="${REPO}/phases/index/index_build.json"
if [[ ! -f "${INDEX_MANIFEST}" ]]; then
  echo ""
  echo "==> Index not built yet. After setup, run:"
  echo "    ./scripts/refresh-corpus-index.sh"
  echo "    # or: ./phases/index/scripts/run_index_build.sh"
else
  echo "==> Index manifest found."
fi

echo ""
echo "==> Setup complete. Start locally:"
echo "    ./scripts/run_local.sh"
