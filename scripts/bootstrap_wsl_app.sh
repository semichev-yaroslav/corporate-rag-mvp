#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
WITH_EMBEDDER="${WITH_EMBEDDER:-1}"

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "Этот скрипт рассчитан на запуск внутри WSL2."
  exit 1
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Не найден ${PYTHON_BIN}. Установите Python 3.11 внутри WSL2 и повторите."
  exit 1
fi

echo "Используем Python: $("${PYTHON_BIN}" --version)"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Создаю виртуальное окружение в ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

if [[ "${WITH_EMBEDDER}" == "1" ]]; then
  echo "Ставлю зависимости embedder extras"
  python -m pip install -e '.[embedder]'
fi

if [[ ! -f "${ROOT_DIR}/.env" ]]; then
  cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
  echo "Создан .env из .env.example. Заполните токены и пути перед запуском."
fi

echo "Готово."
echo "Дальше:"
echo "1. Заполните ${ROOT_DIR}/.env"
echo "2. Убедитесь, что PostgreSQL и pgvector уже установлены в WSL2"
echo "3. Запустите: ${VENV_DIR}/bin/python ${ROOT_DIR}/scripts/check_stack.py"
