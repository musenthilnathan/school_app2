# Mac deployment setup for TTS_BDS

This is the setup flow for a new Mac machine running this project locally.

## 1) Install prerequisites

Install these first:

- Xcode Command Line Tools
  - `xcode-select --install`
- Homebrew
- Docker Desktop for Mac
- Node.js LTS
- Python 3.12+ (or 3.11/3.12)
- Git

Example:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then:

```bash
brew install python node git
```

Start Docker Desktop and confirm it is running:

```bash
docker --version
docker compose version
```

## 2) Clone the repo

```bash
git clone https://github.com/musenthilnathan/school_app2.git
cd school_app2
```

## 3) Set up the backend Python environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create the backend environment file:

```bash
cat > .env <<'EOF'
PROD=false
DATABASE_URL_DEV=postgresql+psycopg://postgres:postgres@localhost:5432/tts_bds
SECRET_KEY_DEV=dev-secret-key-change-me
DATABASE_URL_PROD=
SECRET_KEY_PROD=
EOF
```

Notes:
- This repo reads `.env` from the `backend/` directory.
- Use `localhost` when running the database from Docker on your Mac.

## 4) Start PostgreSQL

From the repo root:

```bash
cd ..
docker compose up -d db
```

If you prefer the older CLI:

```bash
docker-compose up -d db
```

Check that the database is healthy:

```bash
docker ps
```

You should see the `tts_bds_db` container running.

## 5) Start the backend

From the repo root:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API should be available at:
- http://localhost:8000
- http://localhost:8000/docs

On startup, the app will auto-create tables and seed initial data.

## 6) Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

The frontend should be available at:
- http://localhost:5173

## 7) One-command startup option

This repo also includes a startup helper:

```bash
cd /path/to/school_app2
./start.sh
```

This script starts:
- Postgres via Docker
- frontend build if needed
- backend via uvicorn
- checks for ngrok
- launches DBeaver if installed locally

Use `./start.sh --build` when you want to force a fresh frontend build.

## 8) Useful project commands

Backup database + export student status workbook:

```bash
./backup_db.sh
```

This creates files in the `backups/` folder:
- timestamped SQL dump
- timestamped Excel workbook with a Summary tab and Students Data tab

Stop app stack:

```bash
./stop.sh
```

Reset local data (if needed):

```bash
python backend/reset_db.py
```

## 9) Troubleshooting

### Docker not found

Make sure Docker Desktop is running, then restart your terminal.

### Python dependency errors

Recreate the venv and reinstall:

```bash
cd backend
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Database connection issues

Verify the DB is running and the `.env` URL matches:

```bash
DATABASE_URL_DEV=postgresql+psycopg://postgres:postgres@localhost:5432/tts_bds
```

### Frontend not loading

Confirm you ran:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

## 10) Standard developer flow

For normal local work on a Mac:

```bash
cd /path/to/school_app2

docker compose up -d db
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then in another terminal:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

If you want a single command to start the full stack, use:

```bash
./start.sh
```
