#!/usr/bin/env bash
# First-time setup + run for TTS_BDS on a Mac/Linux machine using a LOCAL PostgreSQL (no Docker).
#
# What it does:
#   1. Checks prerequisites (psql, python3, node, npm) and that PostgreSQL is running
#   2. Creates the `tts_bds` database (if missing) and optionally restores a backup into it
#   3. Creates backend/.venv, installs backend + frontend dependencies, creates .env files
#   4. Starts the backend (port 8000) and the frontend (port 5173)
#
# The book_inventories table (and its starting rows) is created automatically by the
# backend on first start, so no extra SQL is needed.
#
# Usage:
#   ./setup_local.sh                              # empty database, app seeds demo data
#   ./setup_local.sh --restore ~/Downloads/tts_bds_db_backup_YYYYMMDD_HHMMSS.sql
#   ./setup_local.sh --restore FILE --force       # replace an existing tts_bds database
#   ./setup_local.sh --no-run                     # set everything up but do not start the app

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_NAME="tts_bds"
DB_USER="postgres"
DB_PASS="postgres"
DB_HOST="localhost"
DB_PORT="5432"
export PGPASSWORD="$DB_PASS"

RESTORE_FILE=""
FORCE=false
RUN=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --restore) RESTORE_FILE="${2:-}"; shift 2 ;;
    --force)   FORCE=true; shift ;;
    --no-run)  RUN=false; shift ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1 (try --help)" >&2; exit 1 ;;
  esac
done

step() { echo ""; echo "==> $*"; }
die()  { echo "ERROR: $*" >&2; exit 1; }
psql_pg() { psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$@"; }

# ---------------------------------------------------------------- prerequisites
step "Checking prerequisites"
for cmd in psql python3 node npm; do
  command -v "$cmd" >/dev/null 2>&1 || die "'$cmd' not found. See README.md > Prerequisites."
done

if [[ -n "$RESTORE_FILE" ]]; then
  RESTORE_FILE="${RESTORE_FILE/#\~/$HOME}"
  [[ -f "$RESTORE_FILE" ]] || die "Backup file not found: $RESTORE_FILE"
fi

pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1 \
  || die "PostgreSQL is not running on $DB_HOST:$DB_PORT. On a Mac: brew services start postgresql@15"

if ! psql_pg -d postgres -c "SELECT 1" >/dev/null 2>&1; then
  echo "    Cannot log in as '$DB_USER' with password '$DB_PASS'. Trying to create that role..."
  psql -h "$DB_HOST" -p "$DB_PORT" -d postgres -c \
    "CREATE ROLE $DB_USER WITH SUPERUSER LOGIN PASSWORD '$DB_PASS';" >/dev/null 2>&1 \
    || psql -h "$DB_HOST" -p "$DB_PORT" -d postgres -c \
    "ALTER ROLE $DB_USER WITH SUPERUSER LOGIN PASSWORD '$DB_PASS';" >/dev/null 2>&1 \
    || die "Could not set up the '$DB_USER' role. Run: psql -d postgres -c \"CREATE ROLE postgres WITH SUPERUSER LOGIN PASSWORD 'postgres';\""
  psql_pg -d postgres -c "SELECT 1" >/dev/null 2>&1 || die "Still cannot log in as '$DB_USER'."
fi
echo "    PostgreSQL is up and the '$DB_USER' login works."

# ---------------------------------------------------------------- database
step "Preparing database '$DB_NAME'"
db_exists() { [[ "$(psql_pg -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")" == "1" ]]; }
table_count() { psql_pg -d "$DB_NAME" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"; }

if [[ -n "$RESTORE_FILE" ]]; then
  if db_exists && [[ "$(table_count)" != "0" ]]; then
    if [[ "$FORCE" == true ]]; then
      echo "    --force given: dropping existing '$DB_NAME'"
      psql_pg -d postgres -c "DROP DATABASE \"$DB_NAME\" WITH (FORCE);" >/dev/null
    else
      die "Database '$DB_NAME' already has tables. Re-run with --force to replace it, or omit --restore."
    fi
  fi
  db_exists || psql_pg -d postgres -c "CREATE DATABASE \"$DB_NAME\";" >/dev/null
  echo "    Restoring $RESTORE_FILE ..."
  psql_pg -d "$DB_NAME" -v ON_ERROR_STOP=1 -q -f "$RESTORE_FILE" >/dev/null
  echo "    Restore complete. Tables: $(table_count)"
else
  if db_exists; then
    echo "    Database '$DB_NAME' already exists, leaving it as is."
  else
    psql_pg -d postgres -c "CREATE DATABASE \"$DB_NAME\";" >/dev/null
    echo "    Created empty database '$DB_NAME' (the app creates its tables on first start)."
  fi
fi

# ---------------------------------------------------------------- backend setup
step "Setting up backend"
cd "$ROOT/backend"
[[ -d .venv ]] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
[[ -f .env ]] || cp .env.example .env
# The app needs the psycopg3 driver prefix; a plain postgresql:// URL silently falls back to SQLite.
perl -pi -e 's#^(DATABASE_URL_DEV=)postgresql://#$1postgresql+psycopg://#' .env
echo "    Backend dependencies installed; .env ready."

# ---------------------------------------------------------------- frontend setup
step "Setting up frontend"
cd "$ROOT/frontend"
[[ -d node_modules ]] || npm install --silent
[[ -f .env ]] || { [[ -f .env.example ]] && cp .env.example .env; } || true
echo "    Frontend dependencies installed."

if [[ "$RUN" != true ]]; then
  echo ""
  echo "Setup finished. To run later:"
  echo "  Terminal 1:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
  echo "  Terminal 2:  cd frontend && npm run dev -- --host 0.0.0.0"
  exit 0
fi

# ---------------------------------------------------------------- run
step "Starting the app"
if lsof -i :8000 >/dev/null 2>&1; then
  die "Port 8000 is already in use. Stop the old backend first: lsof -ti :8000 | xargs kill"
fi

cd "$ROOT/backend"
BACKEND_LOG="/tmp/tts_bds_backend.log"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT INT TERM

echo "    Waiting for the backend (log: $BACKEND_LOG)"
for _ in $(seq 1 40); do
  curl -sf http://localhost:8000/health >/dev/null 2>&1 && break
  kill -0 "$BACKEND_PID" 2>/dev/null || { tail -20 "$BACKEND_LOG"; die "Backend stopped unexpectedly."; }
  sleep 1
done
curl -sf http://localhost:8000/health >/dev/null 2>&1 || { tail -20 "$BACKEND_LOG"; die "Backend did not become healthy."; }

# Confirm the backend is really talking to PostgreSQL and not the SQLite fallback.
if [[ -f "$ROOT/backend/tts_bds.db" ]]; then
  echo "    WARNING: backend/tts_bds.db exists, so the app may be using SQLite instead of PostgreSQL."
  echo "             Check DATABASE_URL_DEV in backend/.env and delete that file."
fi
echo "    Book inventory rows: $(psql_pg -d "$DB_NAME" -tAc 'SELECT count(*) FROM book_inventories' 2>/dev/null || echo '?')"

echo ""
echo "==> App is up"
echo "    Frontend: http://localhost:5173"
echo "    API docs: http://localhost:8000/docs"
echo "    Press Ctrl+C to stop both."
echo ""
cd "$ROOT/frontend"
npm run dev -- --host 0.0.0.0
