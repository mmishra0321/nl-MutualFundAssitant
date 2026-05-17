#!/usr/bin/env bash
# Local equivalent of .github/workflows/refresh-corpus-index.yml
# GitHub schedule: daily 10:00 IST (cron 30 4 * * * UTC)
# Phase 0 validate → Phase 1.5 corpus → Phase 2.5 index
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
CORPUS="${REPO}/phases/corpus"
INDEX="${REPO}/phases/index"
FOUNDATIONS="${REPO}/phases/foundations"

export HF_HOME="${HF_HOME:-${INDEX}/.cache/huggingface}"
export PYTHONPATH="${CORPUS}:${INDEX}${PYTHONPATH:+:${PYTHONPATH}}"

if [[ -x "${INDEX}/.venv/bin/python" ]]; then
  PY="${INDEX}/.venv/bin/python"
elif [[ -x "${CORPUS}/.venv/bin/python" ]]; then
  PY="${CORPUS}/.venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi

echo "==> MS02 scheduled refresh (local)"
echo "    Repo: ${REPO}"
echo "    Python: ${PY}"
echo "    HF_HOME: ${HF_HOME}"
echo ""

echo "==> [1/3] Validate allowlist (Phase 0)"
bash "${FOUNDATIONS}/validate_allowlist.sh"
echo ""

echo "==> [2/3] Phase 1.5 — re-crawl corpus (fetch → extract → normalize)"
cd "${CORPUS}"
export PYTHONPATH="${CORPUS}${PYTHONPATH:+:${PYTHONPATH}}"
"${PY}" -m ms02_corpus.p1_5_pipeline
echo ""

echo "==> [3/3] Phase 2.5 — rebuild index (chunk → embed → Chroma → golden tests)"
cd "${INDEX}"
export PYTHONPATH="${INDEX}:${CORPUS}${PYTHONPATH:+:${PYTHONPATH}}"
"${PY}" -m ms02_index.p2_5_pipeline
echo ""

echo "==> Refresh complete."
echo "    Corpus manifests: ${CORPUS}/normalized/*/manifest.json"
echo "    Index manifest:   ${INDEX}/index_build.json"
