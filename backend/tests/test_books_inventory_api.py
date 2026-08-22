import pytest

from tests.conftest import as_user, client


def test_list_books_returns_catalog():
    """Test that listing books returns the catalog."""
    with as_user("books_team_lead"):
        response = client.get("/books")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] > 0
        assert len(data["items"]) > 0
        
        # Check structure of first book
        book = data["items"][0]
        assert "id" in book
        assert "title" in book
        assert "grade_level" in book
        assert "base_unit_cost" in book


def test_get_book_by_id():
    """Test getting a specific book by ID."""
    with as_user("books_team_lead"):
        response = client.get("/books/BOOK-001")
        assert response.status_code == 200
        book = response.json()
        assert book["id"] == "BOOK-001"
        assert "title" in book


def test_search_books_filters_by_query():
    """Test book search filters by title."""
    with as_user("volunteer", assigned_grade="Grade 6"):
        response = client.get("/books/search?q=Grammar")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Grammar"
        # Should find Grammar books
        assert any("Grammar" in item["title"] for item in data["items"])


def test_list_books_filters_by_grade():
    """Test listing books can be filtered by grade level."""
    with as_user("volunteer", assigned_grade="Grade 6"):
        response = client.get("/books?grade_level=Grade%206")
        assert response.status_code == 200
        data = response.json()
        # All returned books should be Grade 6
        assert all(item["grade_level"] == "Grade 6" for item in data["items"])


def test_list_inventory_returns_records():
    """Test that listing inventory returns records."""
    with as_user("books_team_lead"):
        response = client.get("/inventory")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "academic_year" in data
        assert data["total"] > 0
        
        # Check structure
        inv = data["items"][0]
        assert "id" in inv
        assert "book_id" in inv
        assert "expected_quantity" in inv
        assert "actual_quantity" in inv
        assert "projected_available_inventory" in inv


def test_get_inventory_by_id():
    """Test getting a specific inventory record."""
    with as_user("books_team_lead"):
        response = client.get("/inventory/INV-001")
        assert response.status_code == 200
        inv = response.json()
        assert inv["id"] == "INV-001"
        assert "book" in inv


def test_update_inventory_as_books_lead():
    """Test Books Team Lead can update inventory."""
    with as_user("books_team_lead"):
        response = client.patch(
            "/inventory/INV-001",
            json={"actual_quantity": 50, "rollover_stock": 6},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["inventory"]["actual_quantity"] == 50
        assert data["inventory"]["rollover_stock"] == 6
        # projected should be recalculated: 50 + 6 + spare_stock(2) = 58
        assert data["inventory"]["projected_available_inventory"] == 58


def test_update_inventory_as_volunteer_is_forbidden():
    """Test volunteers cannot update inventory."""
    with as_user("volunteer", assigned_grade="Grade 6"):
        response = client.patch(
            "/inventory/INV-001",
            json={"actual_quantity": 50},
        )
        assert response.status_code == 403


def test_inventory_summary_groups_by_grade():
    """Test inventory summary aggregates by grade level."""
    with as_user("books_team_lead"):
        response = client.get("/inventory/summary/2024-2025")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert data["academic_year"] == "2024-2025"
        
        # Should have multiple grade levels
        assert len(data["summary"]) > 0
        
        # Check structure
        grade_summary = data["summary"][0]
        assert "grade_level" in grade_summary
        assert "total_expected" in grade_summary
        assert "total_actual" in grade_summary
        assert "total_projected" in grade_summary
        assert "discrepancy" in grade_summary
