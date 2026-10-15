from sqlalchemy.orm import Session

from app.db.models import BookInventory

# Initial book counts from inventory_worksheet_Oct4.xlsx
# (grade_level, category, complete_set_count, extra_count)
DEFAULT_BOOK_INVENTORIES = [
    ("Preschool 1", "Textbook", 10, 0),
    ("Preschool 1", "Exercise", 10, 0),
    ("Preschool 2", "Textbook", 14, 0),
    ("Preschool 2", "Exercise", 14, 0),
    ("Kindergarten", "Textbook", 48, 0),
    ("Kindergarten", "Handwriting", 48, 2),
    ("Kindergarten", "Exercise", 48, 3),
    ("Kindergarten", "Vannam Pala Vannam", 40, 0),
    ("Kindergarten", "En Saadhanai", 40, 0),
    ("Kindergarten", "Nee Yaar", 8, 6),
    ("Kindergarten", "Nalla Manam", 8, 6),
    ("Grade 1", "Textbook", 67, 0),
    ("Grade 1", "Handwriting", 67, 0),
    ("Grade 1", "Exercise", 67, 2),
    ("Grade 1", "Idhu Kadikkumaa", 67, 113),
    ("Grade 1", "Kaattil Oru Kudumbam", 67, 67),
    ("Grade 2", "Textbook", 32, 8),
    ("Grade 2", "Handwriting", 33, 9),
    ("Grade 2", "Exercise", 33, 6),
    ("Grade 2", "Enna Suvai", 0, 0),
    ("Grade 2", "En Nanban", 0, 0),
    ("Grade 2", "Malarum Mottum", 0, 2),
    ("Grade 2", "Sutham Sugam Tharum", 14, 0),
    ("Grade 2", "Venduma Vendama", 19, 0),
    ("Grade 3", "Unit 1", 21, 2),
    ("Grade 3", "Unit 2", 21, 2),
    ("Grade 3", "Handwriting", 21, 0),
    ("Grade 3", "Koodu Kattiya Kuyil", 21, 6),
    ("Grade 3", "Moondru Sakkara Vandi", 21, 2),
    ("Grade 4", "Unit 1", 13, 0),
    ("Grade 4", "Unit 2", 13, 0),
    ("Grade 4", "Aattin Madhi Nutpam", 0, 7),
    ("Grade 4", "Noolagam Sendra Nila", 13, 1),
    ("Grade 5", "Textbook & Exercise", 15, 0),
    ("Grade 5", "Enge Selvathu", 15, 11),
    ("Grade 5", "Ammaavin Anbu", 15, 5),
    ("Grade 6", "Unit 1", 23, 1),
    ("Grade 6", "Unit 2", 23, 1),
    ("Grade 6", "Midhivandiyai Virumbiya Madhi", 23, 7),
    ("Grade 6", "Pagalil Vizhiththirundha Aandhai", 23, 7),
    ("Grade 7", "Unit 1", 11, 0),
    ("Grade 7", "Unit 2", 11, 0),
    ("Grade 7", "Povomaa Oorvalam: Bangalore", 11, 2),
    ("Grade 7", "Povomaa Oorvalam: Chennai", 11, 43),
    ("Grade 8", "Unit 1", 3, 0),
    ("Grade 8", "Unit 2", 3, 0),
    ("Grade 8", "Povomaa Oorvalam: San Francisco", 3, 64),
    ("Grade 8", "Povomaa Oorvalam: Madurai", 3, 46),
]


def seed_book_inventories(db: Session) -> None:
    """Load the initial book inventory rows, only when the table is empty.

    The table itself is created at startup by Base.metadata.create_all. Skipping when
    rows already exist means a restored database, or counts edited in the app, are
    never overwritten.
    """
    if db.query(BookInventory).count() > 0:
        return
    db.add_all(
        BookInventory(
            grade_level=grade,
            category=category,
            complete_set_count=complete,
            extra_count=extra,
        )
        for grade, category, complete, extra in DEFAULT_BOOK_INVENTORIES
    )
    db.commit()
