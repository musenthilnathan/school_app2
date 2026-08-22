import io

from conftest import client, as_user


def test_upload_students_csv_success():
    """Test successful CSV upload with insert and update operations."""
    # Create CSV content
    csv_content = """cta_student_id,full_name,registered_grade_level,school
9001,Arun Kumar,Grade 8,Lincoln Elementary
9002,Priya Sharma,Grade 7,Washington Middle
9003,Raj Patel,Grade 6,Jefferson High
"""
    
    # Upload as admin
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with as_user("admin"):
        response = client.post("/students/upload", files=files)
    
    if response.status_code != 200:
        print("Error response:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["inserted"] == 3
    assert data["summary"]["updated"] == 0
    assert data["summary"]["errors"] == 0


def test_upload_students_update_existing():
    """Test updating existing students via CSV upload."""
    # First upload
    csv_content1 = """cta_student_id,full_name,registered_grade_level,school
9010,Test Student,Grade 6,Old School
"""
    files1 = {"file": ("students1.csv", io.BytesIO(csv_content1.encode()), "text/csv")}
    with as_user("admin"):
        response1 = client.post("/students/upload", files=files1)
    assert response1.status_code == 200
    assert response1.json()["summary"]["inserted"] == 1
    
    # Update the same student (different name and school)
    csv_content2 = """cta_student_id,full_name,registered_grade_level,school
9010,Updated Student Name,Grade 7,New School
"""
    files2 = {"file": ("students2.csv", io.BytesIO(csv_content2.encode()), "text/csv")}
    with as_user("admin"):
        response2 = client.post("/students/upload", files=files2)
    
    assert response2.status_code == 200
    data = response2.json()
    assert data["summary"]["inserted"] == 0
    assert data["summary"]["updated"] == 1
    assert data["summary"]["errors"] == 0
    
    # Verify the update
    with as_user("admin"):
        search_response = client.get("/students/search?q=9010")
    students = search_response.json()["items"]
    assert len(students) == 1
    assert students[0]["full_name"] == "Updated Student Name"
    assert students[0]["registered_grade_level"] == "Grade 7"
    assert students[0]["school"] == "New School"


def test_upload_students_missing_columns():
    """Test CSV upload with missing required columns."""
    csv_content = """cta_student_id,full_name
9020,Missing Grade
"""
    
    files = {"file": ("bad.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with as_user("admin"):
        response = client.post("/students/upload", files=files)
    
    assert response.status_code == 400
    assert "Could not find required columns" in response.json()["detail"] or "Missing" in response.json()["detail"]


def test_upload_students_invalid_data():
    """Test CSV upload with invalid data in rows."""
    csv_content = """cta_student_id,full_name,registered_grade_level
invalid_id,Student Name,Grade 8
9021,,Grade 7
9022,Valid Student,Grade 6
"""
    
    files = {"file": ("mixed.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with as_user("admin"):
        response = client.post("/students/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    # Only the valid row should be inserted
    assert data["summary"]["inserted"] == 1
    assert data["summary"]["errors"] == 2


def test_upload_students_unauthorized_volunteer():
    """Test that volunteers cannot upload students."""
    csv_content = """cta_student_id,full_name,registered_grade_level
9030,Student,Grade 6
"""
    
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with as_user("volunteer", assigned_grade="Grade 6"):
        response = client.post("/students/upload", files=files)
    
    assert response.status_code == 403
    assert "Only admin and books team lead" in response.json()["detail"]


def test_upload_students_books_lead_allowed():
    """Test that books team lead can upload students."""
    csv_content = """cta_student_id,full_name,registered_grade_level
9031,Student Via Lead,Grade 8
"""
    
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with as_user("books_team_lead"):
        response = client.post("/students/upload", files=files)
    
    assert response.status_code == 200
    assert response.json()["summary"]["inserted"] == 1


def test_upload_students_invalid_file_type():
    """Test upload with invalid file type."""
    txt_content = b"This is not a CSV file"
    
    files = {"file": ("students.txt", io.BytesIO(txt_content), "text/plain")}
    with as_user("admin"):
        response = client.post("/students/upload", files=files)
    
    assert response.status_code == 400
    assert "File must be CSV or Excel" in response.json()["detail"]


def test_upload_students_empty_file():
    """Test upload with empty CSV file."""
    csv_content = ""
    
    files = {"file": ("empty.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with as_user("admin"):
        response = client.post("/students/upload", files=files)
    
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
