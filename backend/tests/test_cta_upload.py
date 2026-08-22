import io

from conftest import client, as_user


def test_upload_cta_format_with_separate_names():
    """Test upload with CTA format: Student ID, Student First Name, Student Last Name, Grade Name."""
    csv_content = """Student ID,Student First Name,Student Last Name,Grade Name,School Name
58921,Riya,Naveenprabu,Grade 8,NJ Thiruvalluvar Tamil School
59263,Shriram,Advaita,Grade 7,Edison Tamil School
58915,Siddhik,Muthu Raman,Grade 6,Roosevelt Academy
"""
    
    files = {"file": ("cta_students.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with as_user("admin"):
        response = client.post("/students/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["inserted"] == 3
    assert data["summary"]["updated"] == 0
    assert data["summary"]["errors"] == 0
    
    # Verify names were combined
    with as_user("admin"):
        search = client.get("/students/search?q=Riya")
    students = search.json()["items"]
    assert len(students) == 1
    assert students[0]["name"] == "Riya Naveenprabu"


def test_upload_cta_format_updates_existing():
    """Test that CTA format can update existing students."""
    # First upload with our format
    csv1 = """cta_student_id,full_name,registered_grade_level,school
70001,Old Name,Grade 8,Old School
"""
    files1 = {"file": ("setup.csv", io.BytesIO(csv1.encode()), "text/csv")}
    with as_user("admin"):
        response1 = client.post("/students/upload", files=files1)
    assert response1.status_code == 200
    assert response1.json()["summary"]["inserted"] == 1
    
    # Update with CTA format
    csv2 = """Student ID,Student First Name,Student Last Name,Grade Name,School Name
70001,Updated,Student,Grade 9,New School
"""
    files2 = {"file": ("cta_update.csv", io.BytesIO(csv2.encode()), "text/csv")}
    with as_user("admin"):
        response2 = client.post("/students/upload", files=files2)
    
    assert response2.status_code == 200
    data = response2.json()
    assert data["summary"]["inserted"] == 0
    assert data["summary"]["updated"] == 1
    
    # Verify update
    with as_user("admin"):
        search = client.get("/students/search?q=70001")
    students = search.json()["items"]
    assert len(students) == 1
    assert students[0]["name"] == "Updated Student"
    assert students[0]["grade"] == "Grade 9"
    assert students[0]["school"] == "New School"


def test_upload_mixed_formats():
    """Test that both formats can be uploaded to same database."""
    # Upload with CTA format
    csv1 = """Student ID,Student First Name,Student Last Name,Grade Name
80001,John,Doe,Grade 7
"""
    files1 = {"file": ("cta.csv", io.BytesIO(csv1.encode()), "text/csv")}
    with as_user("admin"):
        response1 = client.post("/students/upload", files=files1)
    assert response1.json()["summary"]["inserted"] == 1
    
    # Upload with our format
    csv2 = """cta_student_id,full_name,registered_grade_level
80002,Jane Smith,Grade 8
"""
    files2 = {"file": ("our.csv", io.BytesIO(csv2.encode()), "text/csv")}
    with as_user("admin"):
        response2 = client.post("/students/upload", files=files2)
    assert response2.json()["summary"]["inserted"] == 1
    
    # Both should be searchable
    with as_user("admin"):
        search = client.get("/students/search?q=80")
    students = search.json()["items"]
    assert len(students) == 2
