# TTS_BDS

Tamil School Book Distribution System: student registration, book inventory and distribution.

## Stack
- FastAPI (backend, `backend/`)
- React + Vite (frontend, `frontend/`)
- PostgreSQL

For a fresh Mac using Docker, see [MAC_DEPLOY_INSTRUCTIONS.md](MAC_DEPLOY_INSTRUCTIONS.md).

---

## First-time setup (Mac or Linux, local PostgreSQL, no Docker)

### 1. Install prerequisites (once)

```bash
brew install postgresql@15 python node git
brew services start postgresql@15
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc   # Intel Mac: /usr/local/opt/...
```

Homebrew's PostgreSQL creates a login named after your Mac user, not `postgres`. The app expects
`postgres` / `postgres`, so create it (the setup script also tries to do this for you):

```bash
psql -d postgres -c "CREATE ROLE postgres WITH SUPERUSER LOGIN PASSWORD 'postgres';"
```

### 2. Get the code

```bash
git clone https://github.com/musenthilnathan/school_app2.git
cd school_app2
```

### 3. Set up and run, in one command

Starting from a database backup (the usual case; use your newest `tts_bds_db_backup_*.sql`):

```bash
./setup_local.sh --restore ~/Downloads/tts_bds_db_backup_YYYYMMDD_HHMMSS.sql
```

Starting with an empty database (the app creates its tables and loads demo data):

```bash
./setup_local.sh
```

The script creates the `tts_bds` database, restores the backup if you gave one, creates `backend/.venv`,
installs backend and frontend dependencies, writes `backend/.env`, starts the backend, and starts the
frontend. When it prints **App is up**, open:

- App: http://localhost:5173
- API docs: http://localhost:8000/docs

Press `Ctrl+C` to stop both. To run again later, just run `./setup_local.sh` (it skips finished steps).

Useful options:

| Option | What it does |
|---|---|
| `--restore FILE` | Restore a `.sql` backup into a new `tts_bds` database |
| `--force` | With `--restore`: replace an existing `tts_bds` database. **Deletes its current data.** |
| `--no-run` | Do the setup only, do not start the app |

Without `--force`, the script refuses to restore over a database that already has tables.

### Book inventory table

The `book_inventories` table is part of the app, like `students` and `books`. The backend creates it
on startup and loads the initial rows (from `backend/app/db/seed_book_inventories.py`) only if the table
is empty. Restoring a backup, restarting, or pulling new code never overwrites existing counts. No extra
SQL script is needed.

### Logging in

Use an account that exists in the restored database. On a brand-new empty database the app creates
demo accounts; see `backend/app/db/seed_users.py`.

---

## Manual setup (what the script does)

```bash
# Database
psql -U postgres -h localhost -d postgres -c "CREATE DATABASE tts_bds;"
psql -U postgres -h localhost -d tts_bds -v ON_ERROR_STOP=1 -f ~/Downloads/tts_bds_db_backup_YYYYMMDD_HHMMSS.sql

# Backend (terminal 1)
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Skip the `psql ... -f` restore line to start with an empty database.

## Using Docker for PostgreSQL instead

```bash
docker compose up -d db
```
Then follow the backend and frontend steps above (skip creating the database).

---

## Checks

```bash
curl http://localhost:8000/health
psql -U postgres -h localhost -d tts_bds -c "\dt"
psql -U postgres -h localhost -d tts_bds -c "SELECT count(*) FROM book_inventories;"
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `Address already in use` (port 8000) | An old backend is running: `lsof -ti :8000 \| xargs kill` |
| `psql: command not found` | Add PostgreSQL to PATH (step 1) and open a new terminal |
| `database "tts_bds" is being accessed by other users` | Close DBeaver / VS Code SQL connections, or use `--force` |
| App shows old or empty data | The backend may have fallen back to SQLite. Check that `DATABASE_URL_DEV` in `backend/.env` starts with `postgresql+psycopg://` and that `backend/tts_bds.db` does not exist |
| Backend runs but cannot reach Postgres | `pg_isready`, then `brew services restart postgresql@15` |
