#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUPERVISOR_CONF="${ROOT_DIR}/deploy/supervisord.conf"
SUPERVISOR_SOCK="${ROOT_DIR}/var/run/supervisor.sock"

install -d -o ragapp -g ragapp "${ROOT_DIR}/var/log"
install -d -o ragapp -g ragapp "${ROOT_DIR}/var/run"
install -d -o ragapp -g ragapp "${ROOT_DIR}/var/cache/huggingface"

if [[ ! -f "${ROOT_DIR}/.env" ]]; then
  echo "Не найден ${ROOT_DIR}/.env"
  exit 1
fi

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  echo "Не найдено виртуальное окружение в ${ROOT_DIR}/.venv"
  exit 1
fi

service postgresql start >/dev/null 2>&1 || true

if [[ -S "${SUPERVISOR_SOCK}" ]]; then
  supervisorctl -c "${SUPERVISOR_CONF}" reread >/dev/null 2>&1 || true
  supervisorctl -c "${SUPERVISOR_CONF}" update >/dev/null 2>&1 || true
else
  supervisord -c "${SUPERVISOR_CONF}"
  sleep 3
fi

supervisorctl -c "${SUPERVISOR_CONF}" start embedder api telegram-bot >/dev/null 2>&1 || true
sleep 5
supervisorctl -c "${SUPERVISOR_CONF}" status
