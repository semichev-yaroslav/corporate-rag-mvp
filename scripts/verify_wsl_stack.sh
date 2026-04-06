#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "Скрипт нужно запускать внутри WSL2."
  exit 1
fi

echo "WSL2: ok"
echo "Kernel: $(uname -r)"

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "GPU:"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
  echo "GPU: nvidia-smi не найден"
fi

for cmd in python3 curl; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "Команда $cmd: ok"
  else
    echo "Команда $cmd: отсутствует"
  fi
done

if command -v psql >/dev/null 2>&1; then
  echo "PostgreSQL client: ok"
else
  echo "PostgreSQL client: отсутствует"
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "Виртуальное окружение не найдено. Сначала выполните scripts/bootstrap_wsl_app.sh"
  exit 1
fi

"${VENV_DIR}/bin/python" "${ROOT_DIR}/scripts/check_stack.py"
