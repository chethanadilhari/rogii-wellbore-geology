#!/usr/bin/env bash
# Start API + frontend in the background (Unix / Git Bash).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/tmp/local_stack"
mkdir -p "${LOG_DIR}"

RELOAD_FLAG=()
if [[ "${1:-}" == "--reload" ]]; then
  RELOAD_FLAG=(--reload)
fi

echo "Starting API (background)..."
bash "${SCRIPT_DIR}/start-api.sh" "${RELOAD_FLAG[@]}" \
  >"${LOG_DIR}/api.log" 2>&1 &
API_PID=$!
echo "${API_PID}" >"${LOG_DIR}/api.pid"

echo "Starting frontend (background)..."
bash "${SCRIPT_DIR}/start-frontend.sh" \
  >"${LOG_DIR}/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "${FRONTEND_PID}" >"${LOG_DIR}/frontend.pid"

echo "API pid=${API_PID}  frontend pid=${FRONTEND_PID}"
echo "Logs: ${LOG_DIR}/api.log , ${LOG_DIR}/frontend.log"
echo "Health check: bash scripts/local/health-check.sh"
echo "Stop: kill \$(cat ${LOG_DIR}/api.pid) \$(cat ${LOG_DIR}/frontend.pid)"
