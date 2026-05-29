#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if [ -f ".env" ]; then
  # shellcheck disable=SC1091
  source ".env"
fi

export LOG_FILE="${LOG_FILE:-${ROOT_DIR}/trending.log}"
mkdir -p "$(dirname "${LOG_FILE}")"

export SPIDER_SCHEDULER_ENABLED="${SPIDER_SCHEDULER_ENABLED:-true}"
export SPIDER_SCHEDULE_TIMES="${SPIDER_SCHEDULE_TIMES:-07:50,15:50,23:50}"
export SPIDER_RUN_ON_STARTUP="${SPIDER_RUN_ON_STARTUP:-false}"

HOST="${BACKEND_HOST:-0.0.0.0}"
PORT="${BACKEND_PORT:-8000}"

exec uvicorn api:app --host "${HOST}" --port "${PORT}"
