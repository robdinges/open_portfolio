#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$PWD}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RESTART_TOUCH_FILE="${RESTART_TOUCH_FILE:-$APP_DIR/tmp/restart.txt}"

cd "$APP_DIR"

mkdir -p "$APP_DIR/tmp" "$APP_DIR/shared" "$APP_DIR/shared/logs"

if [[ ! -d .venv ]]; then
"$PYTHON_BIN" -m venv --without-pip .venv
fi

if [[ ! -x .venv/bin/pip ]]; then
curl -fsS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
.venv/bin/python /tmp/get-pip.py
fi

.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# Shared-hosting style app restart (Passenger-compatible)
if [[ -n "$RESTART_TOUCH_FILE" ]]; then
  mkdir -p "$(dirname "$RESTART_TOUCH_FILE")"
  touch "$RESTART_TOUCH_FILE"
fi

echo "Shared-host deploy completed"
