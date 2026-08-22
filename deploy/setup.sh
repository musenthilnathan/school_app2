#!/usr/bin/env bash
# First-time prod setup. Run this ONCE on the prod machine, from the repo root
# (the repo must already be `git clone`d there, checked out to `main`).
#
# On a fresh Ubuntu machine with nothing installed, run
# deploy/bootstrap_ubuntu.sh instead - it installs OS packages/Postgres and
# then calls this script automatically. Use this script directly only if
# Python/Node/Postgres are already set up (e.g. a managed/hosted database).
#
# What it does:
#   1. Verifies you're on the `main` branch (prod always deploys from `main`).
#   2. Creates the backend Python venv and installs dependencies.
#   3. Ensures backend/.env exists and PROD=true is set before continuing.
#   4. Checks the prod database is reachable.
#   5. Builds the frontend (frontend/dist) for the backend to serve.
#   6. Installs + starts the systemd service (if systemd is available).
#
# Safe to re-run; it will not touch existing database data.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Checking branch"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "ERROR: prod must run from 'main', currently on '$CURRENT_BRANCH'." >&2
  echo "Run: git checkout main && git pull" >&2
  exit 1
fi

echo "==> Setting up backend venv"
cd "$REPO_ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "==> Checking backend/.env"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created backend/.env from .env.example. Fill in PROD=true, DATABASE_URL_PROD," >&2
  echo "and SECRET_KEY_PROD, then re-run this script." >&2
  exit 1
fi

if ! grep -qE '^PROD=true$' .env; then
  echo "ERROR: backend/.env must have PROD=true for a prod deployment." >&2
  exit 1
fi

if ! grep -qE '^DATABASE_URL_PROD=.+' .env || ! grep -qE '^SECRET_KEY_PROD=.+' .env; then
  echo "ERROR: DATABASE_URL_PROD and SECRET_KEY_PROD must be set in backend/.env." >&2
  exit 1
fi

echo "==> Verifying prod database is reachable"
python3 - <<'PYEOF'
from app.core.config import get_settings
from sqlalchemy import create_engine, text

settings = get_settings()
engine = create_engine(settings.database_url_prod, pool_pre_ping=True)
with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
print("Database connection OK.")
PYEOF

echo "==> Building frontend"
cd "$REPO_ROOT/frontend"
npm ci
npm run build

echo "==> Installing systemd service (if available)"
if command -v systemctl &>/dev/null; then
  sudo cp "$REPO_ROOT/deploy/tts-bds.service" /etc/systemd/system/tts-bds.service
  sudo sed -i "s#__REPO_ROOT__#$REPO_ROOT#g" /etc/systemd/system/tts-bds.service
  sudo systemctl daemon-reload
  sudo systemctl enable tts-bds
  sudo systemctl restart tts-bds
  echo "Service started. Check status with: sudo systemctl status tts-bds"
else
  echo "systemd not found. Start the app manually with:"
  echo "  cd $REPO_ROOT/backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
fi

echo "==> Setup complete."
