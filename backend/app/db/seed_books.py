from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import Book, Inventory

# Sample Tamil textbooks for different grades
DEFAULT_BOOKS = [
    {
        "id": "BOOK-001",
        "title": "Tamil Ilakkiyam Grade 6",
        "publisher_code": "CTA-TN-2024",
        "grade_level": "Grade 6",
        "base_unit_cost": Decimal("15.50"),
    },
    {
        "id": "BOOK-002",
        "title": "Tamil Ilakkiyam Grade 7",
        "publisher_code": "CTA-TN-2024",
        "grade_level": "Grade 7",
        "base_unit_cost": Decimal("16.00"),
    },
    {
        "id": "BOOK-003",
        "title": "Tamil Ilakkiyam Grade 8",
        "publisher_code": "CTA-TN-2024",
        "grade_level": "Grade 8",
        "base_unit_cost": Decimal("16.50"),
    },
    {
        "id": "BOOK-004",
        "title": "Tamil Ilakkiyam Grade 9",
        "publisher_code": "CTA-TN-2024",
        "grade_level": "Grade 9",
        "base_unit_cost": Decimal("17.00"),
    },
    {
        "id": "BOOK-005",
        "title": "Tamil Ilakkiyam Grade 10",
        "publisher_code": "CTA-TN-2024",
        "grade_level": "Grade 10",
        "base_unit_cost": Decimal("17.50"),
    },
    {
        "id": "BOOK-006",
        "title": "Tamil Grammar Grade 6",
        "publisher_code": "CTA-TN-2024",
        "grade_level": "Grade 6",
        "base_unit_cost": Decimal("12.00"),
    },
    {
        "id": "BOOK-007",
        "title": "Tamil Grammar Grade 7",
        "publisher_code": "CTA-TN-2024",
        "grade_level": "Grade 7",
        "base_unit_cost": Decimal("12.50"),
    },
    {
        "id": "BOOK-008",
        "title": "Tamil Grammar Grade 8",
        "publisher_code": "CTA-TN-2024",
        "grade_level": "Grade 8",
        "base_unit_cost": Decimal("13.00"),
    },
]

# Sample inventory for 2024-2025 academic year
DEFAULT_INVENTORIES = [
    {
        "id": "INV-001",
        "academic_year": "2024-2025",
        "book_id": "BOOK-001",
        "expected_quantity": 50,
        "actual_quantity": 48,
        "rollover_stock": 5,
        "spare_stock": 2,
        "invoice_shipping_cost": Decimal("25.00"),
        "projected_available_inventory": 55,  # 48 + 5 + 2
    },
    {
        "id": "INV-002",
        "academic_year": "2024-2025",
        "book_id": "BOOK-002",
        "expected_quantity": 45,
        "actual_quantity": 45,
        "rollover_stock": 3,
        "spare_stock": 1,
        "invoice_shipping_cost": Decimal("22.50"),
        "projected_available_inventory": 49,  # 45 + 3 + 1
    },
    {
        "id": "INV-003",
        "academic_year": "2024-2025",
        "book_id": "BOOK-003",
        "expected_quantity": 60,
        "actual_quantity": 58,
        "rollover_stock": 4,
        "spare_stock": 2,
        "invoice_shipping_cost": Decimal("30.00"),
        "projected_available_inventory": 64,  # 58 + 4 + 2
    },
    {
        "id": "INV-004",
        "academic_year": "2024-2025",
        "book_id": "BOOK-004",
        "expected_quantity": 40,
        "actual_quantity": 40,
        "rollover_stock": 2,
        "spare_stock": 1,
        "invoice_shipping_cost": Decimal("20.00"),
        "projected_available_inventory": 43,  # 40 + 2 + 1
    },
    {
        "id": "INV-005",
        "academic_year": "2024-2025",
        "book_id": "BOOK-005",
        "expected_quantity": 35,
        "actual_quantity": 35,
        "rollover_stock": 3,
        "spare_stock": 0,
        "invoice_shipping_cost": Decimal("17.50"),
        "projected_available_inventory": 38,  # 35 + 3 + 0
    },
]


def seed_books(db: Session) -> None:
    """Seed books table with default book catalog."""
    if db.query(Book).count() > 0:
        return

    for item in DEFAULT_BOOKS:
        db.add(Book(**item))
    db.commit()


def seed_inventories(db: Session) -> None:
    """Seed inventories table with default inventory data."""
    if db.query(Inventory).count() > 0:
        return

    for item in DEFAULT_INVENTORIES:
        db.add(Inventory(**item))
    db.commit()
