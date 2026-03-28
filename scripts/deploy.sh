#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$PWD}"
BRANCH="${BRANCH:-main}"
SERVICE_NAME="${SERVICE_NAME:-openportfolio}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$APP_DIR"

git fetch --all --prune
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/pip install -r requirements.txt

PYTHONPATH=src .venv/bin/python -m pytest tests/ -q

sudo systemctl daemon-reload
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl --no-pager --full status "$SERVICE_NAME" | head -n 25

curl -fsS "http://127.0.0.1:5000/healthz" >/dev/null
echo "Deploy completed successfully"
