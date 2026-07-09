#!/usr/bin/env bash
set -euo pipefail

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

check_port() {
  local port="$1"
  echo "== 端口 ${port} =="
  if ! lsof -nP -iTCP:"${port}" -sTCP:LISTEN; then
    echo "未发现监听进程"
  fi
  echo
}

check_port "${POSTGRES_PORT}"
check_port "${BACKEND_PORT}"
check_port "${FRONTEND_PORT}"

if [ "${FRONTEND_PORT}" != "5173" ]; then
  check_port "5173"
fi
