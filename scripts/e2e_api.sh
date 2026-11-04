#!/usr/bin/env bash
# Start an isolated SelectIQ API for Playwright: a fresh temporary data root and SQLite
# database, and CORS for the e2e web port. By default it uses main's offline adapters
# (deterministic encoder and scripted reasoner), which the app labels "Test signals, not AI".
# With SELECTIQ_E2E_REAL_AI=1 it uses OpenCLIP and Groq (GROQ_API_KEY from the environment or .env).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

api_port="${SELECTIQ_E2E_API_PORT:-8765}"
web_port="${SELECTIQ_E2E_WEB_PORT:-5174}"
python="backend/.venv/bin/python"
[[ -x "$python" ]] || python="python3"

data_root="$(mktemp -d "${TMPDIR:-/tmp}/selectiq-e2e.XXXXXX")"
trap 'rm -rf "$data_root"' EXIT

export SELECTIQ_DATA_ROOT="$data_root"
export SELECTIQ_DATABASE_URL="sqlite:///$data_root/selectiq.sqlite3"
export SELECTIQ_CORS_ORIGINS="http://localhost:$web_port,http://127.0.0.1:$web_port"
if [[ "${SELECTIQ_E2E_REAL_AI:-0}" == "1" ]]; then
  export SELECTIQ_MODEL_ADAPTER=openclip SELECTIQ_REASONER=groq
else
  export SELECTIQ_MODEL_ADAPTER=fake SELECTIQ_REASONER=fake
fi

"$python" -m alembic -c backend/alembic.ini upgrade head
"$python" -m uvicorn selectiq.api.main:app --app-dir backend/src --host 127.0.0.1 --port "$api_port"
