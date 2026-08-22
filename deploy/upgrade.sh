#!/usr/bin/env bash
# Refresh/upgrade the prod deployment to the latest `main` without losing data.
#
# What it does:
#   1. Pulls the latest `main` (fast-forward only; aborts if history diverged).
#   2. Reinstalls backend dependencies (in case requirements.txt changed).
#   3. Rebuilds the frontend.
#   4. Restarts the service.
#
# Data safety: the app creates missing tables on startup (SQLAlchemy
# `create_all`) but NEVER drops or alters existing tables/rows, so upgrading
# code never touches existing prod data. Note: this also means it does NOT
# handle schema changes that require altering existing columns/tables - if a
# future change needs that, add a real migration tool (e.g. Alembic) first.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "ERROR: prod must run from 'main', currently on '$CURRENT_BRANCH'." >&2
  exit 1
fi

echo "==> Pulling latest main"
git fetch origin
git pull --ff-only origin main

echo "==> Updating backend dependencies"
cd "$REPO_ROOT/backend"
source .venv/bin/activate
pip install --quiet -r requirements.txt

echo "==> Rebuilding frontend"
cd "$REPO_ROOT/frontend"
npm ci
npm run build

echo "==> Restarting service"
if command -v systemctl &>/dev/null; then
  sudo systemctl restart tts-bds
  echo "Restarted. Check status with: sudo systemctl status tts-bds"
else
  echo "systemd not found. Restart your manually-run uvicorn process."
fi

echo "==> Verifying health"
sleep 2
curl -sf http://localhost:8000/health && echo || echo "WARNING: health check failed, inspect logs."

echo "==> Upgrade complete. Database data untouched."
