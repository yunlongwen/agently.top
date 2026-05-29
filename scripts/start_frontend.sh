#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"

cd "${FRONTEND_DIR}"

if [ ! -d "node_modules" ]; then
  echo "frontend/node_modules 不存在，请先运行: cd frontend && npm install" >&2
  exit 1
fi

HOST="${FRONTEND_HOST:-127.0.0.1}"
PORT="${FRONTEND_PORT:-8080}"

exec npm run serve -- --host "${HOST}" --port "${PORT}"
