from app.db.models import BookInventory
from tests.conftest import TestingSessionLocal, as_user, client


def _seed_rows():
    db = TestingSessionLocal()
    try:
        if db.query(BookInventory).count() == 0:
            db.add_all([
                BookInventory(grade_level="Grade 1", category="Textbook", complete_set_count=67, extra_count=0),
                BookInventory(grade_level="Grade 1", category="Handwriting", complete_set_count=67, extra_count=2),
                BookInventory(grade_level="Grade 2", category="Textbook", complete_set_count=32, extra_count=8),
            ])
            db.commit()
        return [i.id for i in db.query(BookInventory).order_by(BookInventory.id).all()]
    finally:
        db.close()


def test_list_and_filter():
    _seed_rows()
    with as_user("volunteer", assigned_grade="Grade 1"):
        data = client.get("/book-inventories").json()
        assert data["total"] == 3
        assert data["grade_levels"] == ["Grade 1", "Grade 2"]
        assert data["total_complete_sets"] == 166

        data = client.get("/book-inventories?grade_level=Grade 1").json()
        assert data["total"] == 2

        data = client.get("/book-inventories?q=hand").json()
        assert [i["category"] for i in data["items"]] == ["Handwriting"]


def test_update_requires_lead_or_admin():
    item_id = _seed_rows()[0]
    with as_user("volunteer", assigned_grade="Grade 1"):
        assert client.patch(f"/book-inventories/{item_id}", json={"extra_count": 5}).status_code == 403
    with as_user("books_team_lead"):
        res = client.patch(f"/book-inventories/{item_id}", json={"extra_count": 5})
        assert res.status_code == 200
        assert res.json()["extra_count"] == 5
        assert client.patch(f"/book-inventories/{item_id}", json={"extra_count": -1}).status_code == 422
        assert client.patch("/book-inventories/999999", json={"extra_count": 1}).status_code == 404
