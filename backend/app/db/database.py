from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()


def _resolve_database_url() -> str:
    database_url = settings.database_url
    if database_url.startswith("postgres"):
        try:
            engine = create_engine(database_url, pool_pre_ping=True)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return database_url
        except Exception:
            return "sqlite:///./tts_bds.db"
    return database_url


resolved_database_url = _resolve_database_url()
engine_args = {"connect_args": {"check_same_thread": False}} if resolved_database_url.startswith("sqlite") else {}
engine = create_engine(resolved_database_url, pool_pre_ping=True, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
