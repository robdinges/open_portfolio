#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <app_dir>"
  exit 1
fi

APP_DIR="$1"
APP_USER="${APP_USER:-$USER}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SERVICE_NAME="openportfolio"

sudo mkdir -p "$APP_DIR" "$APP_DIR/shared" "$APP_DIR/shared/logs" "$APP_DIR/shared/run"
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

if [[ ! -d "$APP_DIR/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$APP_DIR/.venv"
fi

echo "Bootstrap completed for $APP_DIR"
echo "Next: copy deploy/systemd/openportfolio.service to /etc/systemd/system/ and deploy/nginx/openportfolio.conf to /etc/nginx/sites-available/."
