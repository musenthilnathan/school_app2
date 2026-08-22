from conftest import as_user, client


def test_student_search_returns_filtered_candidates():
    with as_user("admin"):
        response = client.get("/students/search?q=sen")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any("Senthil" in student["name"] for student in payload["items"])


def test_student_approval_updates_status():
    with as_user("admin"):
        response = client.post("/students/approve?student_id=TTS-1001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["student"]["status"] == "APPROVED"


def test_grade_queue_returns_matching_students():
    with as_user("admin"):
        response = client.get("/students/queue?grade=Grade%208")
    assert response.status_code == 200
    payload = response.json()
    assert payload["grade"] == "Grade 8"
    assert any(student["grade"] == "Grade 8" for student in payload["items"])
