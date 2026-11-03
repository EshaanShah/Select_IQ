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
docker compose up -d --wait postgres
python3 -m alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend/src uvicorn selectiq.api.main:app --reload --port 8000 &
api_pid=$!

npm --prefix frontend run dev

