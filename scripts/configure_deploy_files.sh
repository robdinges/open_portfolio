#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "Usage: $0 <app_user> <app_dir> <server_name> <output_dir>"
  echo "Example: $0 deploy /srv/open-portfolio portfolio.example.com /tmp/openportfolio-deploy"
  exit 1
fi

APP_USER="$1"
APP_DIR="$2"
SERVER_NAME="$3"
OUTPUT_DIR="$4"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_TEMPLATE="$ROOT_DIR/deploy/systemd/openportfolio.service"
NGINX_TEMPLATE="$ROOT_DIR/deploy/nginx/openportfolio.conf"

if [[ ! -f "$SYSTEMD_TEMPLATE" ]]; then
  echo "Missing template: $SYSTEMD_TEMPLATE"
  exit 1
fi

if [[ ! -f "$NGINX_TEMPLATE" ]]; then
  echo "Missing template: $NGINX_TEMPLATE"
  exit 1
fi

mkdir -p "$OUTPUT_DIR/systemd" "$OUTPUT_DIR/nginx"

SYSTEMD_OUT="$OUTPUT_DIR/systemd/openportfolio.service"
NGINX_OUT="$OUTPUT_DIR/nginx/openportfolio.conf"

sed \
  -e "s|__APP_USER__|$APP_USER|g" \
  -e "s|__APP_DIR__|$APP_DIR|g" \
  "$SYSTEMD_TEMPLATE" > "$SYSTEMD_OUT"

if grep -q "server_name _;" "$NGINX_TEMPLATE"; then
  sed -e "s|server_name _;|server_name $SERVER_NAME;|g" "$NGINX_TEMPLATE" > "$NGINX_OUT"
else
  cp "$NGINX_TEMPLATE" "$NGINX_OUT"
fi

echo "Generated files:"
echo "- $SYSTEMD_OUT"
echo "- $NGINX_OUT"

echo "Next steps:"
echo "1) Copy systemd file to /etc/systemd/system/openportfolio.service"
echo "2) Copy nginx file to /etc/nginx/sites-available/openportfolio.conf"
echo "3) Enable and restart services"
