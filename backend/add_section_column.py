"""
Migration script to add section column to students table.
Run this once to update existing database schema.
"""
from sqlalchemy import text
from app.db.database import engine

def add_section_column():
    """Add section column to students table if it doesn't exist."""
    with engine.connect() as connection:
        # Check if column exists
        result = connection.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='students' AND column_name='section'
        """))
        
        if result.fetchone() is None:
            # Add column
            connection.execute(text("""
                ALTER TABLE students 
                ADD COLUMN section VARCHAR(50)
            """))
            connection.commit()
            print("✅ Successfully added 'section' column to students table")
        else:
            print("ℹ️  Column 'section' already exists in students table")

if __name__ == "__main__":
    add_section_column()
