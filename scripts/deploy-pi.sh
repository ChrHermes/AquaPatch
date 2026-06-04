#!/usr/bin/env bash
set -euo pipefail

PI_HOST="${PI_HOST:-aquapatch}"
PI_USER="${PI_USER:-christopher}"
PI_KEY="${PI_KEY:-/Users/christopher/.ssh/id_ed25519}"
REMOTE_DIR="${REMOTE_DIR:-/home/christopher/aquapatch}"
SETUP_ARGS=()

usage() {
  cat <<'USAGE'
Usage: scripts/deploy-pi.sh [--real-hardware] [--skip-setup]

Environment overrides:
  PI_HOST      default: aquapatch
  PI_USER      default: christopher
  PI_KEY       default: /Users/christopher/.ssh/id_ed25519
  REMOTE_DIR   default: /home/christopher/aquapatch

Options:
  --real-hardware   Set HARDWARE_MOCK=false on the Pi when creating backend/.env.
  --skip-setup      Only rsync the files; do not run scripts/setup-pi.sh remotely.
USAGE
}

RUN_SETUP=true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --real-hardware)
      SETUP_ARGS+=("--real-hardware")
      shift
      ;;
    --skip-setup)
      RUN_SETUP=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSH_TARGET="${PI_USER}@${PI_HOST}"
SSH_OPTS=(-i "$PI_KEY")

echo "Deploying AquaPatch to ${SSH_TARGET}:${REMOTE_DIR}"
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "mkdir -p '$REMOTE_DIR'"

rsync -az --delete \
  -e "ssh -i ${PI_KEY}" \
  --exclude ".git/" \
  --exclude ".DS_Store" \
  --exclude "backend/.venv/" \
  --exclude "backend/.env" \
  --exclude "backend/aquapatch.db" \
  --exclude "frontend/node_modules/" \
  --exclude "frontend/dist/" \
  --exclude "tmp/" \
  "$ROOT_DIR/" "${SSH_TARGET}:${REMOTE_DIR}/"

if [[ "$RUN_SETUP" == "true" ]]; then
  REMOTE_SETUP_CMD="cd '$REMOTE_DIR' && bash scripts/setup-pi.sh"
  if [[ ${#SETUP_ARGS[@]} -gt 0 ]]; then
    REMOTE_SETUP_CMD="${REMOTE_SETUP_CMD} ${SETUP_ARGS[*]}"
  fi
  ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "$REMOTE_SETUP_CMD"
else
  echo "Skipped remote setup. Run on the Pi: cd '$REMOTE_DIR' && bash scripts/setup-pi.sh"
fi

echo "Deployment finished. Open: http://${PI_HOST}:8000"
