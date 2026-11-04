#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  if [[ -n "${api_pid:-}" ]]; then
    kill "$api_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

cd "$repo_root"
python_bin="backend/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  echo "backend/.venv is missing. Follow the README setup steps first." >&2
  exit 1
fi

"$python_bin" -m alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend/src "$python_bin" -m uvicorn selectiq.api.main:app --reload --port 8000 &
api_pid=$!

npm --prefix frontend run dev

