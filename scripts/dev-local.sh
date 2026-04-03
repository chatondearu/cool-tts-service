#!/usr/bin/env bash
# Run FastAPI (generator) and Nuxt UI together for local testing outside Docker.
#
# Prerequisites:
#   - Project .venv with generator/requirements_api.txt installed (provides uvicorn),
#     or uvicorn on PATH
#   - ui/node_modules — run once: (cd ui && npm install)
#   - ui/.env — copy from ui/.env.example; set NUXT_SESSION_PASSWORD (≥32 chars),
#     NUXT_ADMIN_PASSWORD, etc.
#   - NUXT_API_BASE_URL in ui/.env must match this API (default in .env.example:
#     http://localhost:9000). If you change API_PORT, set e.g.
#     NUXT_API_BASE_URL=http://127.0.0.1:<port>
#
# Usage: from repo root
#   ./scripts/dev-local.sh
#   API_PORT=9000 UI_PORT=3001 ./scripts/dev-local.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="${API_PORT:-9000}"
UI_PORT="${UI_PORT:-3000}"

if [[ ! -d "$ROOT/ui/node_modules" ]]; then
  echo "dev-local.sh: ui/node_modules missing — run: (cd ui && npm install)" >&2
  exit 1
fi

if [[ -x "$ROOT/.venv/bin/uvicorn" ]]; then
  UVICORN="$ROOT/.venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
  UVICORN="uvicorn"
else
  echo "dev-local.sh: uvicorn not found — install generator/requirements_api.txt into .venv or PATH" >&2
  exit 1
fi

API_PID=""
cleanup() {
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup INT TERM EXIT

(
  cd "$ROOT/generator"
  exec "$UVICORN" main:app --reload --host 0.0.0.0 --port "$API_PORT"
) &
API_PID=$!

cd "$ROOT/ui"
npm run dev -- --port "$UI_PORT"
