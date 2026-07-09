#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.local-run"
LOG_DIR="${RUN_DIR}/logs"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
CONDA_ENV="${CONDA_ENV:-esa}"
DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://postgres:postgres@localhost:${POSTGRES_PORT}/enterprise_support_agent}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-http://localhost:${FRONTEND_PORT}}"
NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:${BACKEND_PORT}}"

mkdir -p "${LOG_DIR}"

export BACKEND_DIR
export FRONTEND_DIR
export DATABASE_URL
export FRONTEND_ORIGIN
export NEXT_PUBLIC_API_BASE_URL
export POSTGRES_PORT
export BACKEND_PORT
export FRONTEND_PORT
export CONDA_ENV
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-replace-with-dev-secret}"
export STORAGE_DIR="${STORAGE_DIR:-app/storage}"
export RAG_SIMILARITY_THRESHOLD="${RAG_SIMILARITY_THRESHOLD:-0.1}"

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    return 127
  fi
}

port_in_use() {
  lsof -tiTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

echo "启动本地开发环境"

if port_in_use "${POSTGRES_PORT}"; then
  echo "数据库端口 ${POSTGRES_PORT} 已有服务，跳过 Docker 数据库启动"
else
  echo "启动 Docker PostgreSQL 数据库..."
  if ! docker_compose up -d db; then
    echo "数据库启动失败。请确认 Docker Desktop 已打开，或手动启动本机 PostgreSQL。"
    exit 1
  fi
fi

if port_in_use "${BACKEND_PORT}"; then
  echo "后端端口 ${BACKEND_PORT} 已有服务，跳过后端启动"
else
  if ! command -v conda >/dev/null 2>&1; then
    echo "未找到 conda。请先在终端初始化 conda，或手动进入 esa 环境启动后端。"
    exit 1
  fi

  echo "启动后端：http://localhost:${BACKEND_PORT}"
  nohup bash -lc 'cd "${BACKEND_DIR}" && conda run --no-capture-output -n "${CONDA_ENV}" python -m uvicorn app.main:app --reload --host 127.0.0.1 --port "${BACKEND_PORT}"' > "${LOG_DIR}/backend.log" 2>&1 &
  echo "$!" > "${RUN_DIR}/backend.pid"
fi

if port_in_use "${FRONTEND_PORT}"; then
  echo "前端端口 ${FRONTEND_PORT} 已有服务，跳过前端启动"
else
  if [ ! -d "${ROOT_DIR}/frontend/node_modules" ]; then
    echo "前端依赖尚未安装。请先执行：cd ${ROOT_DIR}/frontend && npm install"
    exit 1
  fi

  echo "启动前端：http://localhost:${FRONTEND_PORT}"
  nohup bash -lc 'cd "${FRONTEND_DIR}" && npm run dev -- -p "${FRONTEND_PORT}" -H 127.0.0.1' > "${LOG_DIR}/frontend.log" 2>&1 &
  echo "$!" > "${RUN_DIR}/frontend.pid"
fi

echo
echo "访问地址："
echo "- 前端：http://localhost:${FRONTEND_PORT}"
echo "- 登录页：http://localhost:${FRONTEND_PORT}/login"
echo "- 后端健康检查：http://localhost:${BACKEND_PORT}/health"
echo
echo "日志位置：${LOG_DIR}"
echo "停止服务：./scripts/stop-local.sh"
