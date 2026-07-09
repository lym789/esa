#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    return 127
  fi
}

stop_port() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN || true)"
  if [ -z "${pids}" ]; then
    echo "端口 ${port} 没有监听进程"
    return
  fi

  echo "关闭端口 ${port}: ${pids//$'\n'/ }"
  kill ${pids} || true
  sleep 1

  pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN || true)"
  if [ -n "${pids}" ]; then
    echo "端口 ${port} 仍被占用，强制关闭: ${pids//$'\n'/ }"
    kill -9 ${pids} || true
  fi
}

cd "${ROOT_DIR}"

stop_port "${BACKEND_PORT}"
stop_port "${FRONTEND_PORT}"

if [ "${FRONTEND_PORT}" != "5173" ]; then
  stop_port "5173"
fi

if lsof -tiTCP:"${POSTGRES_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "尝试停止 Docker PostgreSQL 数据库"
  docker_compose stop db >/dev/null 2>&1 || true
fi

echo "本地服务停止流程已执行"
