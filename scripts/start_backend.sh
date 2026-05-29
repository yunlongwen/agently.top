#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="/root/logs/github-python"

cd "${ROOT_DIR}"

if [ -f "${HOME}/.bash_profile" ]; then
  # shellcheck disable=SC1090
  source "${HOME}/.bash_profile"
fi

if [ -f ".env" ]; then
  # shellcheck disable=SC1091
  source ".env"
fi

mkdir -p "${LOG_DIR}"

export LOG_FILE="${LOG_FILE:-${LOG_DIR}/trending.log}"
BACKEND_LOG="${BACKEND_LOG:-${LOG_DIR}/backend.out}"

export SPIDER_SCHEDULER_ENABLED="${SPIDER_SCHEDULER_ENABLED:-true}"
export SPIDER_SCHEDULE_TIMES="${SPIDER_SCHEDULE_TIMES:-07:50,15:50,23:50}"
export SPIDER_RUN_ON_STARTUP="${SPIDER_RUN_ON_STARTUP:-false}"

HOST="${BACKEND_HOST:-0.0.0.0}"
PORT="${BACKEND_PORT:-8000}"

python3 -m pip install -r requirements.txt

OLD_PIDS="$(ps -ef | awk '/[u]vicorn api:app/ {print $2}')"
if [ -n "${OLD_PIDS}" ]; then
  kill ${OLD_PIDS}
  sleep 2
fi

nohup python3 -m uvicorn api:app --host "${HOST}" --port "${PORT}" > "${BACKEND_LOG}" 2>&1 &
NEW_PID="$!"

sleep 2

if ps -p "${NEW_PID}" > /dev/null 2>&1; then
  echo "Backend started successfully. pid=${NEW_PID}, port=${PORT}, log=${BACKEND_LOG}, app_log=${LOG_FILE}"
else
  echo "Backend failed to start. Check log: ${BACKEND_LOG}" >&2
  exit 1
fi
