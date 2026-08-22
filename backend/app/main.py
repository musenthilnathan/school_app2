from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.auth import router as auth_router
from app.api.routes.books import router as books_router
from app.api.routes.health import router as health_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.students import router as students_router
from app.core.config import get_settings
from app.db.database import Base, SessionLocal, engine
from app.db.seed import seed_students
from app.db.seed_books import seed_books, seed_inventories
from app.db.seed_users import seed_users

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="TTS_BDS backend API",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_users(db)
        seed_books(db)
        seed_inventories(db)
        seed_students(db)
    finally:
        db.close()


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(books_router)
app.include_router(inventory_router)

# Serve the built frontend (frontend/dist) so a single process can run in prod.
# Mounted last so it only catches requests the API routers above didn't match.
_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
else:

    @app.get("/")
    def root():
        return {"message": "TTS_BDS backend is running"}
