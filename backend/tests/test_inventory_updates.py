"""Inventory (book_inventories) must follow student handover, return and swap actions."""
import contextlib

from app.db.models import BookInventory, Student, StudentStatus
from tests.conftest import TestingSessionLocal, as_user, client

OLD_GRADE = "Grade 91"
NEW_GRADE = "Grade 92"
_next_id = [7_000_000]


@contextlib.contextmanager
def inventory(rows):
    """Create BookInventory rows for the test and always clean them up afterwards."""
    db = TestingSessionLocal()
    try:
        ids = []
        for grade, category, sets in rows:
            row = BookInventory(grade_level=grade, category=category, complete_set_count=sets, extra_count=0)
            db.add(row)
            db.flush()
            ids.append(row.id)
        db.commit()
        yield
    finally:
        db.query(BookInventory).filter(BookInventory.grade_level.in_({g for g, _, _ in rows})).delete(
            synchronize_session=False
        )
        db.commit()
        db.close()


def counts(grade):
    db = TestingSessionLocal()
    try:
        rows = db.query(BookInventory).filter(BookInventory.grade_level == grade).order_by(BookInventory.id).all()
        return {r.category: r.complete_set_count for r in rows}
    finally:
        db.close()


def make_student(grade, status, handed_over_grade=None):
    _next_id[0] += 1
    n = _next_id[0]
    db = TestingSessionLocal()
    try:
        db.add(
            Student(
                id=f"TEST-INV-{n}",
                tts_student_id=n,
                cta_student_id=n,
                full_name=f"Inventory Test {n}",
                school="Test School",
                registered_grade_level=grade,
                status=status,
                book_handed_over_grade=handed_over_grade,
            )
        )
        db.commit()
        return f"TEST-INV-{n}"
    finally:
        db.close()


def test_handover_reduces_only_that_grades_inventory():
    with inventory([(OLD_GRADE, "Textbook", 10), (OLD_GRADE, "Workbook", 5), (NEW_GRADE, "Textbook", 7)]):
        sid = make_student(OLD_GRADE, StudentStatus.APPROVED.value)
        with as_user("admin"):
            res = client.post(f"/students/handoff?student_id={sid}")
        assert res.status_code == 200
        assert counts(OLD_GRADE) == {"Textbook": 9, "Workbook": 4}
        assert counts(NEW_GRADE) == {"Textbook": 7}


def test_handover_blocked_when_out_of_stock():
    with inventory([(OLD_GRADE, "Textbook", 3), (OLD_GRADE, "Workbook", 0)]):
        sid = make_student(OLD_GRADE, StudentStatus.APPROVED.value)
        with as_user("admin"):
            res = client.post(f"/students/handoff?student_id={sid}")
        assert res.status_code == 409
        assert "Workbook" in res.json()["detail"]
        # Nothing changed: counts intact and student not marked handed over.
        assert counts(OLD_GRADE) == {"Textbook": 3, "Workbook": 0}
        db = TestingSessionLocal()
        try:
            assert db.get(Student, sid).status == StudentStatus.APPROVED.value
        finally:
            db.close()


def test_handover_without_inventory_rows_still_works():
    sid = make_student("Grade 93", StudentStatus.APPROVED.value)
    with as_user("admin"):
        res = client.post(f"/students/handoff?student_id={sid}")
    assert res.status_code == 200


def test_return_increases_inventory_of_issued_grade():
    with inventory([(OLD_GRADE, "Textbook", 10), (OLD_GRADE, "Workbook", 5)]):
        sid = make_student(
            OLD_GRADE, StudentStatus.WITHDRAWN_BOOK_NOT_RETURNED.value, handed_over_grade=OLD_GRADE
        )
        with as_user("books_team_lead"):
            res = client.post(f"/students/return?student_id={sid}")
        assert res.status_code == 200
        assert counts(OLD_GRADE) == {"Textbook": 11, "Workbook": 6}


def test_swap_increases_current_grade_and_reduces_upgrade_grade():
    """Student holds an OLD_GRADE book and has moved up to NEW_GRADE (PENDING_SWAP)."""
    with inventory([(OLD_GRADE, "Textbook", 10), (NEW_GRADE, "Textbook", 10)]):
        sid = make_student(NEW_GRADE, StudentStatus.PENDING_SWAP.value, handed_over_grade=OLD_GRADE)

        # Step 1: old book comes back -> current (old) grade goes up, upgrade grade untouched yet.
        with as_user("books_team_lead"):
            assert client.post(f"/students/return?student_id={sid}").status_code == 200
        assert counts(OLD_GRADE) == {"Textbook": 11}
        assert counts(NEW_GRADE) == {"Textbook": 10}

        # Step 2: new book is approved and handed over -> upgrade grade goes down.
        with as_user("books_team_lead"):
            assert client.post(f"/students/approve?student_id={sid}").status_code == 200
            assert client.post(f"/students/handoff?student_id={sid}").status_code == 200
        assert counts(OLD_GRADE) == {"Textbook": 11}
        assert counts(NEW_GRADE) == {"Textbook": 9}
