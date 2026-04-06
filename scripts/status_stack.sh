#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUPERVISOR_CONF="${ROOT_DIR}/deploy/supervisord.conf"
SUPERVISOR_SOCK="${ROOT_DIR}/var/run/supervisor.sock"

echo "== PostgreSQL =="
service postgresql status 2>/dev/null || true
echo

echo "== Supervisor =="
if [[ -S "${SUPERVISOR_SOCK}" ]]; then
  supervisorctl -c "${SUPERVISOR_CONF}" status || true
else
  echo "supervisord не запущен"
fi
echo

echo "== Stack Check =="
if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/scripts/check_stack.py"
else
  echo "Виртуальное окружение не найдено"
fi
