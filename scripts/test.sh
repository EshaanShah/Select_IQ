#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_bin="python3"
if [[ -x backend/.venv/bin/python ]]; then
  python_bin="backend/.venv/bin/python"
fi

"$python_bin" -m compileall -q backend/src scripts

if "$python_bin" -c "import pytest" 2>/dev/null; then
  PYTHONPATH=backend/src "$python_bin" -m pytest backend/tests -m "not real_model"
else
  echo "pytest is not installed; Python source compilation passed."
fi

if [[ -d frontend/node_modules ]]; then
  npm --prefix frontend test
else
  echo "frontend/node_modules is absent; frontend tests were not run."
fi

if [[ -d node_modules ]]; then
  npm run test:e2e
else
  echo "root node_modules is absent; Playwright tests were not run."
fi

