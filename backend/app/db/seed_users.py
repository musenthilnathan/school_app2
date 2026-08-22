import uuid

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.models import User, UserRole

DEFAULT_USERS = [
    {
        "id": str(uuid.uuid4()),
        "username": "admin",
        "email": "admin@tts.org",
        "password": "admin123",
        "role": UserRole.ADMIN.value,
        "assigned_grade": None,
    },
    {
        "id": str(uuid.uuid4()),
        "username": "books_lead",
        "email": "books@tts.org",
        "password": "books123",
        "role": UserRole.BOOKS_TEAM_LEAD.value,
        "assigned_grade": None,
    },
    # Volunteers for each grade
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_ps1",
        "email": "vol_ps1@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "PS1",
    },
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_ps2",
        "email": "vol_ps2@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "PS2",
    },
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_g1",
        "email": "vol1@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "Grade 1",
    },
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_g2",
        "email": "vol2@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "Grade 2",
    },
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_g3",
        "email": "vol3@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "Grade 3",
    },
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_g4",
        "email": "vol4@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "Grade 4",
    },
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_g5",
        "email": "vol5@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "Grade 5",
    },
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_g6",
        "email": "vol6@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "Grade 6",
    },
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_g7",
        "email": "vol7@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "Grade 7",
    },
    {
        "id": str(uuid.uuid4()),
        "username": "volunteer_g8",
        "email": "vol8@tts.org",
        "password": "vol123",
        "role": UserRole.VOLUNTEER.value,
        "assigned_grade": "Grade 8",
    },
]


def seed_users(db: Session) -> None:
    if db.query(User).count() > 0:
        return

    for item in DEFAULT_USERS:
        user_data = item.copy()
        password = user_data.pop("password")
        user_data["password_hash"] = get_password_hash(password)
        db.add(User(**user_data))
    
    db.commit()
