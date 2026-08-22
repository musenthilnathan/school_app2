# TTS_BDS

Implementation design and app scaffold for the Tamil School Book Distribution System.

## Stack
- FastAPI
- React
- PostgreSQL

## Local runtime

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database
```bash
docker compose up -d
```

### Frontend
```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```
