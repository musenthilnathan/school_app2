from sqlalchemy.orm import Session

from app.db.models import Student

DEFAULT_STUDENTS = [
    {
        "id": "TTS-1001",
        "tts_student_id": 1001,
        "cta_student_id": 50001,
        "full_name": "Senthil Kumar",
        "school": "Nallur Govt School",
        "registered_grade_level": "Grade 8",
        "status": "READY_FOR_PICKUP",
        "pending_swap_flag": False,
    },
    {
        "id": "TTS-1002",
        "tts_student_id": 1002,
        "cta_student_id": 50002,
        "full_name": "Sena Devi",
        "school": "Mylapore Tamil School",
        "registered_grade_level": "Grade 7",
        "status": "PENDING_SWAP",
        "pending_swap_flag": True,
    },
    {
        "id": "TTS-1003",
        "tts_student_id": 1003,
        "cta_student_id": 50003,
        "full_name": "Mohan Raj",
        "school": "Nallur Govt School",
        "registered_grade_level": "Grade 9",
        "status": "APPROVED",
        "pending_swap_flag": False,
    },
    {
        "id": "TTS-1004",
        "tts_student_id": 1004,
        "cta_student_id": 50004,
        "full_name": "Sundar Selvi",
        "school": "Anna Nagar School",
        "registered_grade_level": "Grade 6",
        "status": "READY_FOR_PICKUP",
        "pending_swap_flag": False,
    },
    {
        "id": "TTS-1005",
        "tts_student_id": 1005,
        "cta_student_id": 50005,
        "full_name": "Rani Senthil",
        "school": "Chennai Tamil School",
        "registered_grade_level": "Grade 10",
        "status": "PENDING_SWAP",
        "pending_swap_flag": True,
    },
    {
        "id": "TTS-1006",
        "tts_student_id": 1006,
        "cta_student_id": 50006,
        "full_name": "Karthik Nair",
        "school": "Mylapore Tamil School",
        "registered_grade_level": "Grade 8",
        "status": "BOOK_HANDED_OVER",
        "pending_swap_flag": False,
    },
]


def seed_students(db: Session) -> None:
    if db.query(Student).count() > 0:
        return

    for item in DEFAULT_STUDENTS:
        db.add(Student(**item))
    db.commit()
