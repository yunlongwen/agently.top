#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/.runtime"

mkdir -p "${RUNTIME_DIR}"

"${ROOT_DIR}/scripts/start_backend.sh" > "${RUNTIME_DIR}/backend.log" 2>&1 &
echo "$!" > "${RUNTIME_DIR}/backend.pid"

"${ROOT_DIR}/scripts/start_frontend.sh" > "${RUNTIME_DIR}/frontend.log" 2>&1 &
echo "$!" > "${RUNTIME_DIR}/frontend.pid"

echo "backend pid: $(cat "${RUNTIME_DIR}/backend.pid")"
echo "frontend pid: $(cat "${RUNTIME_DIR}/frontend.pid")"
echo "backend log: ${RUNTIME_DIR}/backend.log"
echo "frontend log: ${RUNTIME_DIR}/frontend.log"
