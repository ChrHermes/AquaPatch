#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PID=""

cleanup() {
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo
    echo "Stopping AquaPatch mock backend..."
    kill "${BACKEND_PID}" 2>/dev/null || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

if [[ ! -x "${ROOT_DIR}/backend/.venv/bin/uvicorn" ]]; then
  echo "Backend dependencies are missing."
  echo "Run: cd backend && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/frontend/node_modules" ]]; then
  echo "Frontend dependencies are missing."
  echo "Run: cd frontend && npm install"
  exit 1
fi

echo "Starting AquaPatch mock backend on http://${BACKEND_HOST}:${BACKEND_PORT}"
(
  cd "${ROOT_DIR}/backend"
  HARDWARE_MOCK=true \
  MQTT_ENABLED=false \
  DATABASE_URL="${DATABASE_URL:-sqlite:///./aquapatch.db}" \
  .venv/bin/uvicorn app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
) &
BACKEND_PID=$!

echo "Waiting for backend..."
for _ in {1..40}; do
  if curl -fsS "http://${BACKEND_HOST}:${BACKEND_PORT}/api/system/status" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

if ! curl -fsS "http://${BACKEND_HOST}:${BACKEND_PORT}/api/system/status" >/dev/null 2>&1; then
  echo "Backend did not become reachable on http://${BACKEND_HOST}:${BACKEND_PORT}"
  exit 1
fi

echo "Starting AquaPatch frontend on http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "Open: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "Press Ctrl+C to stop both servers."
(
  cd "${ROOT_DIR}/frontend"
  npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}"
  # npm run dev -- --host --port "${FRONTEND_PORT}"
)
