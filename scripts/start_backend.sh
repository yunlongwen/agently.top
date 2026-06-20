#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="/root/logs/github-python"

cd "${ROOT_DIR}"

source_env_file() {
  local env_file="$1"

  if [ -f "${env_file}" ]; then
    set +u
    # shellcheck disable=SC1090
    source "${env_file}"
    set -u
  fi
}

if [ -f "${HOME}/.bash_profile" ]; then
  source_env_file "${HOME}/.bash_profile"
fi

if [ -f ".env" ]; then
  source_env_file ".env"
fi

mkdir -p "${LOG_DIR}"

export LOG_FILE="${LOG_FILE:-${LOG_DIR}/trending.log}"
BACKEND_LOG="${BACKEND_LOG:-${LOG_DIR}/backend.out}"

export SPIDER_SCHEDULER_ENABLED="${SPIDER_SCHEDULER_ENABLED:-true}"
export SPIDER_SCHEDULE_TIMES="${SPIDER_SCHEDULE_TIMES:-07:50,15:50,23:50}"
export SPIDER_RUN_ON_STARTUP="${SPIDER_RUN_ON_STARTUP:-false}"

HOST="${BACKEND_HOST:-0.0.0.0}"
PORT="${BACKEND_PORT:-8000}"

# 默认使用 python3.11,因 3.6 装不上 fastapi>=0.100,3.8 不支持 PEP 604 语法
# (dict[str, Any] | None)。可通过 PYTHON 环境变量覆盖,例如 PYTHON=python3.12。
PYTHON="${PYTHON:-python3.11}"

"${PYTHON}" -m pip install -r requirements.txt

OLD_PIDS="$(ps -ef | awk '/[u]vicorn api:app/ {print $2}')"
if [ -n "${OLD_PIDS}" ]; then
  kill ${OLD_PIDS}
  sleep 2
fi

nohup "${PYTHON}" -m uvicorn api:app --host "${HOST}" --port "${PORT}" > "${BACKEND_LOG}" 2>&1 &
NEW_PID="$!"

sleep 2

if ps -p "${NEW_PID}" > /dev/null 2>&1; then
  echo "Backend started successfully. pid=${NEW_PID}, port=${PORT}, log=${BACKEND_LOG}, app_log=${LOG_FILE}"
else
  echo "Backend failed to start. Check log: ${BACKEND_LOG}" >&2
  exit 1
fi
