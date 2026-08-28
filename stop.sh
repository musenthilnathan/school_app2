#!/usr/bin/env bash
# Stops the TTS_BDS stack: backend (uvicorn) and Postgres (Docker).
# Leaves ngrok.service running (it's a persistent systemd tunnel, independent
# of the app being up or down). Use `sudo systemctl stop ngrok.service` if you
# want to stop the tunnel too.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "==> Stopping backend (uvicorn)"
if pgrep -f "uvicorn app.main:app" > /dev/null; then
  pkill -f "uvicorn app.main:app"
  echo "    Backend stopped."
else
  echo "    Backend was not running."
fi

echo "==> Stopping Postgres (Docker)"
docker-compose stop db

echo ""
echo "==> Done. (ngrok.service left running - stop separately if needed:"
echo "    sudo systemctl stop ngrok.service)"
