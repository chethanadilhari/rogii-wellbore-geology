#!/usr/bin/env bash
# Start the React/Vite frontend on 127.0.0.1:5173.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_ROOT="${PROJECT_ROOT}/app/frontend"
cd "${FRONTEND_ROOT}"

HOST_ADDRESS="${FRONTEND_HOST:-127.0.0.1}"
PORT="${FRONTEND_PORT:-5173}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST_ADDRESS="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -d "${FRONTEND_ROOT}/node_modules" ]]; then
  echo "Installing frontend dependencies (npm install)..."
  npm install
fi

if [[ ! -f "${FRONTEND_ROOT}/.env" ]]; then
  cp "${FRONTEND_ROOT}/.env.example" "${FRONTEND_ROOT}/.env"
  echo "Created app/frontend/.env from .env.example"
fi

echo "Starting frontend on http://${HOST_ADDRESS}:${PORT}"
echo "Expects API at VITE_API_BASE_URL (default http://127.0.0.1:8000)"

exec npm run dev -- --host "${HOST_ADDRESS}" --port "${PORT}"
