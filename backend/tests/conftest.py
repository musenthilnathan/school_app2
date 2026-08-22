import contextlib
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_current_user
from app.core.security import get_password_hash
from app.db.database import Base, get_db
from app.db.models import User
from app.db.seed import seed_students
from app.db.seed_books import seed_books, seed_inventories
from app.db.seed_users import seed_users
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

Base.metadata.create_all(bind=test_engine)

_seed_db = TestingSessionLocal()
try:
    seed_users(_seed_db)
    seed_books(_seed_db)
    seed_inventories(_seed_db)
    seed_students(_seed_db)
finally:
    _seed_db.close()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Known seeded credentials, matching app.db.seed_users.DEFAULT_USERS
KNOWN_PASSWORDS = {
    "admin": "admin123",
    "books_lead": "books123",
    "volunteer_g6": "vol123",
    "volunteer_g7": "vol123",
    "volunteer_g8": "vol123",
}


def make_user(role: str, assigned_grade: str | None = None, user_id: str | None = None) -> User:
    uid = user_id or f"test-{role}-{uuid.uuid4().hex[:6]}"
    return User(
        id=uid,
        username=f"test_{role}",
        email=f"{uid}@tts.org",
        password_hash=get_password_hash("unused"),
        role=role,
        assigned_grade=assigned_grade,
        is_active=True,
    )


@contextlib.contextmanager
def as_user(role: str, assigned_grade: str | None = None, user_id: str | None = None):
    """Temporarily override the authenticated user for a block of test code."""
    user = make_user(role, assigned_grade, user_id)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield user
    finally:
        app.dependency_overrides.pop(get_current_user, None)
