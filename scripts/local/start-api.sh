#!/usr/bin/env bash
# Start the FastAPI prediction backend on 127.0.0.1:8000.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

HOST_ADDRESS="${API_HOST:-127.0.0.1}"
PORT="${API_PORT:-8000}"
RELOAD=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST_ADDRESS="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --reload) RELOAD=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON="${PROJECT_ROOT}/.venv/bin/python"
elif [[ -x "${PROJECT_ROOT}/.venv/Scripts/python.exe" ]]; then
  PYTHON="${PROJECT_ROOT}/.venv/Scripts/python.exe"
else
  PYTHON="python3"
  echo "Warning: project .venv not found; using ${PYTHON} from PATH." >&2
fi

if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
  cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
  echo "Created .env from .env.example"
fi

if [[ ! -f "${PROJECT_ROOT}/artifacts/current.json" ]]; then
  echo "Missing artifacts/current.json. Train/export first: python scripts/train_export.py" >&2
  exit 1
fi

echo "Starting FastAPI on http://${HOST_ADDRESS}:${PORT}"
echo "OpenAPI docs: http://${HOST_ADDRESS}:${PORT}/docs"

ARGS=(-m uvicorn app.api.main:app --host "${HOST_ADDRESS}" --port "${PORT}")
if [[ "${RELOAD}" -eq 1 ]]; then
  ARGS+=(--reload)
fi

exec "${PYTHON}" "${ARGS[@]}"
