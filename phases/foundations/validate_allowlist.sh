#!/usr/bin/env bash
# Validates Phase 0 allowlist: exactly five canonical Groww mutual-fund URLs.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALLOWLIST="${SCRIPT_DIR}/allowlist.yaml"

if [[ ! -f "${ALLOWLIST}" ]]; then
  echo "error: missing ${ALLOWLIST}" >&2
  exit 1
fi

# Count url: lines that contain the mutual-funds path (one per scheme).
count=$(grep -E '^\s+url:\s+https://groww\.in/mutual-funds/' "${ALLOWLIST}" | wc -l | tr -d ' ')
if [[ "${count}" -ne 5 ]]; then
  echo "error: expected exactly 5 allowlisted Groww URLs, found ${count}" >&2
  exit 1
fi

# Each URL must be unique.
dup=$(grep -E '^\s+url:\s+https://groww\.in/mutual-funds/' "${ALLOWLIST}" | sort | uniq -d | wc -l | tr -d ' ')
if [[ "${dup}" -ne 0 ]]; then
  echo "error: duplicate URLs in allowlist" >&2
  exit 1
fi

echo "allowlist OK (${count} URLs)"
