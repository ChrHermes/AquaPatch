#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/christopher/aquapatch}"
APP_USER="${APP_USER:-christopher}"
SERVICE_NAME="${SERVICE_NAME:-aquapatch-backend}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
REAL_HARDWARE=false

usage() {
  cat <<'USAGE'
Usage: scripts/setup-pi.sh [--real-hardware]

Runs on the Raspberry Pi. It installs system packages, prepares the backend
virtualenv, builds the frontend, installs the systemd service and starts it.

Options:
  --real-hardware   Create backend/.env with HARDWARE_MOCK=false.
                    Without this flag, mock mode remains enabled for safety.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --real-hardware)
      REAL_HARDWARE=true
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

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command is missing: $1" >&2
    exit 1
  fi
}

if [[ ! -d "$APP_DIR/backend" || ! -d "$APP_DIR/frontend" ]]; then
  echo "APP_DIR does not look like an AquaPatch checkout: $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

echo "Running AquaPatch Raspberry Pi preflight"
require_command sudo
require_command "$PYTHON_BIN"

if [[ -e /proc/device-tree/model ]]; then
  MODEL="$(tr -d '\0' </proc/device-tree/model)"
  echo "Detected device: $MODEL"
else
  echo "Could not detect Raspberry Pi model from /proc/device-tree/model"
fi

if [[ ! -e /dev/i2c-1 ]]; then
  echo "I2C device /dev/i2c-1 is not present yet. Enable I2C with: sudo raspi-config"
fi

echo "Installing system packages"
sudo apt-get update
sudo apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  python3-dev \
  build-essential \
  i2c-tools \
  nodejs \
  npm \
  rsync

echo "Preparing backend virtual environment"
"$PYTHON_BIN" -m venv backend/.venv
backend/.venv/bin/python -m pip install --upgrade pip wheel
backend/.venv/bin/pip install -r backend/requirements.txt

if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
  if [[ "$REAL_HARDWARE" == "true" ]]; then
    sed -i 's/^HARDWARE_MOCK=.*/HARDWARE_MOCK=false/' backend/.env
  fi
  echo "Created backend/.env. Review relay polarity and MQTT settings before hardware testing."
else
  echo "Keeping existing backend/.env"
fi

echo "Building frontend"
npm --prefix frontend install
npm --prefix frontend run build

echo "Installing systemd service"
sudo cp backend/systemd/aquapatch-backend.service "/etc/systemd/system/${SERVICE_NAME}.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

if command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
  echo "Opening port 8000/tcp in ufw"
  sudo ufw allow 8000/tcp comment "AquaPatch"
fi

echo "Service status"
sudo systemctl --no-pager --lines=20 status "$SERVICE_NAME" || true

echo "AquaPatch is available at: http://$(hostname -I | awk '{print $1}'):8000"
