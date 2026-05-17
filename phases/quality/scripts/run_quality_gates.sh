#!/usr/bin/env bash
# Phase 5 — hardening / quality gates (needs Phase 2 index for full run).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
PHASES="${REPO}/phases"
P5="${PHASES}/quality"
INDEX="${PHASES}/index"
CORPUS="${PHASES}/corpus"
P3="${PHASES}/answer_engine"
export PYTHONPATH="${P5}:${P3}:${INDEX}:${CORPUS}${PYTHONPATH:+:${PYTHONPATH}}"
export HF_HOME="${HF_HOME:-${INDEX}/.cache/huggingface}"

if [[ -x "${INDEX}/.venv/bin/python" ]]; then PY="${INDEX}/.venv/bin/python"
else PY="${PYTHON:-python3}"; fi

cd "${P5}"
exec "${PY}" -m ms02_hardening "$@"
