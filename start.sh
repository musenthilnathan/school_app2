#!/usr/bin/env bash
# Starts the TTS_BDS stack for training/testing via ngrok.
# - Postgres via Docker Compose
# - Frontend built (if dist/ missing or --build passed) and served by the backend
# - Backend run directly on the host (not Docker) so it can serve frontend/dist
# - Assumes ngrok.service (systemd) is already running/tunneling port 8000
#
# Usage:
#   ./start.sh            # start everything, skip frontend build if dist/ exists
#   ./start.sh --build    # force a fresh frontend build first

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

FORCE_BUILD=false
if [[ "${1:-}" == "--build" ]]; then
  FORCE_BUILD=true
fi

echo "==> Starting Postgres (Docker)"
docker-compose up -d db

echo "==> Waiting for Postgres to be healthy"
for i in {1..15}; do
  if docker-compose ps db | grep -q "healthy"; then
    echo "    Postgres is healthy."
    break
  fi
  sleep 1
done

if [[ "$FORCE_BUILD" == true || ! -d "$REPO_ROOT/frontend/dist" ]]; then
  echo "==> Building frontend"
  cd "$REPO_ROOT/frontend"
  npm run build
  cd "$REPO_ROOT"
else
  echo "==> Skipping frontend build (dist/ already exists, use --build to force)"
fi

echo "==> Starting backend (uvicorn, background)"
cd "$REPO_ROOT/backend"

if [[ -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  echo "    Activating $REPO_ROOT/.venv"
  source "$REPO_ROOT/.venv/bin/activate"
elif ! command -v uvicorn &> /dev/null; then
  echo "ERROR: No .venv found at $REPO_ROOT/.venv and 'uvicorn' not on PATH." >&2
  echo "        Activate your environment first, e.g.: source $REPO_ROOT/.venv/bin/activate" >&2
  exit 1
fi

# Avoid double-starting if already running
if pgrep -f "uvicorn app.main:app" > /dev/null; then
  echo "    Backend already running, skipping."
else
  nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/tts_bds_backend.log 2>&1 &
  disown
  sleep 3
  echo "    Backend started. Logs: /tmp/tts_bds_backend.log"
fi

echo "==> Checking ngrok tunnel"
if systemctl is-active --quiet ngrok.service; then
  echo "    ngrok.service is active."
  sleep 1
  curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*"' || echo "    (could not read tunnel URL yet, check http://localhost:4040)"
else
  echo "    WARNING: ngrok.service is not active. Start it with: sudo systemctl start ngrok.service"
fi

echo ""
echo "==> Quick health check"
sleep 2
curl -sf http://localhost:8000/health && echo "" || echo "    Backend health check failed - check /tmp/tts_bds_backend.log"

echo ""
echo "==> Done. Local URL: http://localhost:8000"
