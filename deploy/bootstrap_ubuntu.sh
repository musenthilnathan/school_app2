#!/usr/bin/env bash
# One-time bootstrap for a FRESH Ubuntu machine with nothing installed yet.
# Installs OS packages (Python, Node, Postgres, git), creates the prod
# Postgres role/database, writes the prod values into backend/.env, then
# runs deploy/setup.sh to finish app-level setup (venv, frontend build,
# systemd service).
#
# Prerequisite: this repo is already `git clone`d on the machine, checked
# out on `main`, and you're running this as a sudo-capable user from the
# repo root:
#   ./deploy/bootstrap_ubuntu.sh
#
# Optional env vars (sane defaults generated if omitted):
#   APP_DB_NAME=tts_bds_prod
#   APP_DB_USER=tts_prod_user
#   APP_DB_PASSWORD=<random hex, generated>
#   SECRET_KEY=<random hex, generated>
#
# If Postgres is already managed elsewhere (e.g. a hosted DB), skip this
# script and run deploy/setup.sh directly after filling in backend/.env
# yourself.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

APP_DB_NAME="${APP_DB_NAME:-tts_bds_prod}"
APP_DB_USER="${APP_DB_USER:-tts_prod_user}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:-$(openssl rand -hex 16)}"
SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"

echo "==> Installing system packages"
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip postgresql postgresql-contrib git curl openssl

if ! command -v node &>/dev/null; then
  echo "==> Installing Node.js 20.x (NodeSource)"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

echo "==> Ensuring Postgres is running"
sudo systemctl enable postgresql
sudo systemctl start postgresql

echo "==> Creating prod database/role (idempotent)"
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${APP_DB_USER}') THEN
    CREATE ROLE ${APP_DB_USER} LOGIN PASSWORD '${APP_DB_PASSWORD}';
  ELSE
    ALTER ROLE ${APP_DB_USER} WITH PASSWORD '${APP_DB_PASSWORD}';
  END IF;
END
\$\$;
SQL

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${APP_DB_NAME}'" | grep -q 1; then
  sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${APP_DB_NAME} OWNER ${APP_DB_USER};"
fi

DATABASE_URL_PROD="postgresql+psycopg://${APP_DB_USER}:${APP_DB_PASSWORD}@localhost:5432/${APP_DB_NAME}"

echo "==> Writing backend/.env prod values"
cd "$REPO_ROOT/backend"
if [[ ! -f .env ]]; then
  cp .env.example .env
fi

set_env_var() {
  local key="$1" value="$2"
  if grep -qE "^${key}=" .env; then
    sed -i "s#^${key}=.*#${key}=${value}#" .env
  else
    echo "${key}=${value}" >>.env
  fi
}

set_env_var "PROD" "true"
set_env_var "DATABASE_URL_PROD" "${DATABASE_URL_PROD}"
set_env_var "SECRET_KEY_PROD" "${SECRET_KEY}"

echo "==> Running app-level setup"
cd "$REPO_ROOT"
./deploy/setup.sh

echo ""
echo "==================================================================="
echo "Bootstrap complete. Save these somewhere safe (password manager):"
echo "  DB name:     ${APP_DB_NAME}"
echo "  DB user:     ${APP_DB_USER}"
echo "  DB password: ${APP_DB_PASSWORD}"
echo "  SECRET_KEY:  ${SECRET_KEY}"
echo "(already written into backend/.env on this machine)"
echo "==================================================================="
