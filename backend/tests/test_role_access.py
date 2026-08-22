from conftest import as_user, client


def test_volunteer_sees_only_assigned_grade_students():
    with as_user("volunteer", assigned_grade="Grade 6"):
        response = client.get("/students")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert all(student["grade"] == "Grade 6" for student in payload["items"])


def test_volunteer_queue_ignores_grade_query_param():
    with as_user("volunteer", assigned_grade="Grade 7"):
        response = client.get("/students/queue?grade=Grade%208")
    assert response.status_code == 200
    payload = response.json()
    assert payload["grade"] == "Grade 7"
    assert all(student["grade"] == "Grade 7" for student in payload["items"])


def test_volunteer_without_assigned_grade_gets_empty_queue():
    with as_user("volunteer", assigned_grade=None):
        response = client.get("/students/queue")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert "message" in payload


def test_volunteer_cannot_approve_student_outside_assigned_grade():
    with as_user("volunteer", assigned_grade="Grade 6"):
        response = client.post("/students/approve?student_id=TTS-1001")
    assert response.status_code == 403


def test_volunteer_can_approve_and_handoff_student_in_assigned_grade():
    with as_user("volunteer", assigned_grade="Grade 6"):
        approve_response = client.post("/students/approve?student_id=TTS-1004")
        assert approve_response.status_code == 200
        assert approve_response.json()["student"]["status"] == "APPROVED"

        handoff_response = client.post("/students/handoff?student_id=TTS-1004")
        assert handoff_response.status_code == 200
        assert handoff_response.json()["student"]["status"] == "BOOK_HANDED_OVER"


def test_books_team_lead_can_approve_student_in_any_grade():
    with as_user("books_team_lead"):
        response = client.post("/students/approve?student_id=TTS-1002")
    assert response.status_code == 200
    assert response.json()["student"]["status"] == "APPROVED"
