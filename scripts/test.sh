#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 -m compileall -q backend/src scripts

if python3 -c "import pytest" 2>/dev/null; then
  docker compose up -d --wait postgres
  selectiq_test_db="selectiq_test_$$"
  cleanup_test_database() {
    docker compose exec -T postgres dropdb --if-exists -U selectiq "$selectiq_test_db" >/dev/null
  }
  trap cleanup_test_database EXIT
  docker compose exec -T postgres createdb -U selectiq "$selectiq_test_db"
  export SELECTIQ_TEST_DATABASE_URL="postgresql+psycopg://selectiq:selectiq@localhost:5432/$selectiq_test_db"
  SELECTIQ_DATABASE_URL="$SELECTIQ_TEST_DATABASE_URL" python3 -m alembic -c backend/alembic.ini upgrade head
  PYTHONPATH=backend/src python3 -m pytest backend/tests
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

