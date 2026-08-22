#!/usr/bin/env python3
"""
Database reset script for development.
Drops all tables and recreates them with seed data.

Usage:
    python reset_db.py
"""

from app.core.config import get_settings
from app.db.database import Base, engine
from app.db.seed import seed_students
from app.db.seed_books import seed_books, seed_inventories
from app.db.seed_users import seed_users
from sqlalchemy.orm import sessionmaker

def reset_database():
    """Drop all tables and recreate with fresh seed data."""
    print("🗑️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("📦 Creating tables with new schema...")
    Base.metadata.create_all(bind=engine)
    
    print("🌱 Seeding database...")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        seed_users(db)
        seed_books(db)
        seed_inventories(db)
        seed_students(db)
        print("✅ Database reset complete!")
        
        # Display seeded users dynamically
        User = __import__('app.db.models', fromlist=['User']).User
        users = db.query(User).order_by(User.role, User.username).all()
        print("\nSeeded users:")
        for user in users:
            grade_info = f", grade: {user.assigned_grade}" if user.assigned_grade else ""
            print(f"  - {user.username} / [password] (role: {user.role}{grade_info})")
        
        print(f"\nSeeded {db.query(__import__('app.db.models', fromlist=['Student']).Student).count()} students")
        print(f"Seeded {db.query(__import__('app.db.models', fromlist=['Book']).Book).count()} books")
        print(f"Seeded {db.query(__import__('app.db.models', fromlist=['Inventory']).Inventory).count()} inventory records")
    finally:
        db.close()

if __name__ == "__main__":
    settings = get_settings()
    print(f"Using database: {settings.database_url}")
    
    confirm = input("\n⚠️  This will DELETE all data. Continue? (yes/no): ")
    if confirm.lower() in ['yes', 'y']:
        reset_database()
    else:
        print("Cancelled.")
