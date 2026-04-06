#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUPERVISOR_CONF="${ROOT_DIR}/deploy/supervisord.conf"
SUPERVISOR_SOCK="${ROOT_DIR}/var/run/supervisor.sock"

if [[ -S "${SUPERVISOR_SOCK}" ]]; then
  supervisorctl -c "${SUPERVISOR_CONF}" shutdown || true
else
  echo "supervisord не запущен"
fi

service postgresql stop >/dev/null 2>&1 || true
