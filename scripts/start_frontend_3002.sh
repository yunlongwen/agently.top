#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
RUNTIME_DIR="${ROOT_DIR}/.runtime"

mkdir -p "${RUNTIME_DIR}"

# Kill old frontend
OLD_PIDS="$(ps -ef | awk '/[v]ue-cli-service serve/ {print $2}')"
if [ -n "${OLD_PIDS}" ]; then
  kill ${OLD_PIDS} 2>/dev/null || true
  sleep 1
fi

cd "${FRONTEND_DIR}"

HOST="${FRONTEND_HOST:-0.0.0.0}"
PORT="${FRONTEND_PORT:-3002}"

nohup node node_modules/.bin/vue-cli-service serve --host "${HOST}" --port "${PORT}" > "${RUNTIME_DIR}/frontend.log" 2>&1 &
echo $! > "${RUNTIME_DIR}/frontend.pid"
echo "Frontend started. pid=$(cat "${RUNTIME_DIR}/frontend.pid"), port=${PORT}"
