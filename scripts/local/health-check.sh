#!/usr/bin/env bash
# Local health check for API (+ optional frontend).
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173}"
SKIP_FRONTEND=0
TIMEOUT=5

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base-url) API_BASE_URL="$2"; shift 2 ;;
    --frontend-url) FRONTEND_URL="$2"; shift 2 ;;
    --skip-frontend) SKIP_FRONTEND=1; shift ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

FAILED=0

pass() { echo "[PASS] $1: $2"; }
fail() { echo "[FAIL] $1: $2"; FAILED=1; }

echo "Local health check"
echo "  API:      ${API_BASE_URL}"
if [[ "${SKIP_FRONTEND}" -eq 0 ]]; then
  echo "  Frontend: ${FRONTEND_URL}"
fi
echo

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

if PY="$(command -v python3 || command -v python || true)"; then
  :
else
  PY=""
fi

HEALTH_BODY="$(curl -fsS --max-time "${TIMEOUT}" "${API_BASE_URL}/health" 2>/dev/null || true)"
if [[ -z "${HEALTH_BODY}" ]]; then
  fail "GET /health" "unreachable"
elif [[ -n "${PY}" ]]; then
  DETAIL="$(HEALTH_JSON="${HEALTH_BODY}" "${PY}" -c '
import json, os
body = json.loads(os.environ["HEALTH_JSON"])
ok = body.get("status") == "healthy" and body.get("model_loaded") is True
detail = (
    f"status={body.get(\"status\")} model_loaded={body.get(\"model_loaded\")} "
    f"version={body.get(\"model_version\")} recipe={body.get(\"selected_model\")}"
)
print("OK" if ok else "BAD")
print(detail)
')"
  STATUS_LINE="$(printf '%s\n' "${DETAIL}" | sed -n '1p')"
  MSG="$(printf '%s\n' "${DETAIL}" | sed -n '2p')"
  if [[ "${STATUS_LINE}" == "OK" ]]; then
    pass "GET /health" "${MSG}"
  else
    fail "GET /health" "${MSG}"
  fi
else
  pass "GET /health" "${HEALTH_BODY}"
fi

MODEL_CODE="$(curl -sS -o /tmp/rogii_models_current.json -w "%{http_code}" --max-time "${TIMEOUT}" "${API_BASE_URL}/models/current" || true)"
if [[ "${MODEL_CODE}" == "200" ]]; then
  pass "GET /models/current" "HTTP 200"
else
  fail "GET /models/current" "HTTP ${MODEL_CODE:-unreachable}"
fi

if [[ "${SKIP_FRONTEND}" -eq 0 ]]; then
  FE_CODE="$(curl -sS -o /dev/null -w "%{http_code}" --max-time "${TIMEOUT}" "${FRONTEND_URL}/" || true)"
  if [[ "${FE_CODE}" == "200" ]]; then
    pass "GET frontend" "HTTP 200"
  else
    fail "GET frontend" "HTTP ${FE_CODE:-unreachable}"
  fi
fi

echo
if [[ "${FAILED}" -ne 0 ]]; then
  echo "Health check FAILED."
  exit 1
fi
echo "Health check OK."
