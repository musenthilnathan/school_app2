#!/usr/bin/env bash
# Resets the database to a clean, freshly-seeded state.
# Wraps backend/reset_db.py. Requires Postgres to be running (start.sh first).
#
# Usage:
#   ./reset.sh          # interactive - asks for confirmation (default, safest)
#   ./reset.sh --yes    # skip confirmation (use with care - e.g. between training sessions)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT/backend"

if [[ -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  source "$REPO_ROOT/.venv/bin/activate"
elif ! command -v python &> /dev/null; then
  echo "ERROR: No .venv found at $REPO_ROOT/.venv and 'python' not on PATH." >&2
  exit 1
fi

echo "==> Confirming Postgres is reachable"
python3 - <<'PYEOF'
from app.core.config import get_settings
from sqlalchemy import create_engine, text

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
print(f"OK - connected to: {settings.database_url}")
PYEOF

if [[ "${1:-}" == "--yes" ]]; then
  echo "==> Resetting database (no prompt, --yes given)"
  python3 - <<'PYEOF'
from app.db.database import Base, engine
from app.db.seed import seed_students
from app.db.seed_books import seed_books, seed_inventories
from app.db.seed_users import seed_users
from sqlalchemy.orm import sessionmaker

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Seeding...")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()
try:
    seed_users(db)
    seed_books(db)
    seed_inventories(db)
    seed_students(db)
    print("Done.")
finally:
    db.close()
PYEOF
else
  echo "==> Running interactive reset (will ask to confirm)"
  python reset_db.py
fi
