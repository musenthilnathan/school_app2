from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import Book, User, UserRole

router = APIRouter(tags=["books"])


@router.get("/books")
def list_books(
    grade_level: str | None = None,
    is_active: bool = True,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List all books in the catalog, optionally filtered by grade level."""
    query = db.query(Book).filter(Book.is_active == is_active)
    
    if grade_level:
        query = query.filter(Book.grade_level.ilike(grade_level))
    
    items = query.order_by(Book.grade_level, Book.title).limit(limit).all()
    total = query.count()
    
    return {"items": [book.to_dict() for book in items], "total": total}


@router.get("/books/search")
def search_books(
    q: str = Query("", min_length=0),
    grade_level: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Search books by title or publisher code."""
    query_str = (q or "").strip()
    
    query = db.query(Book).filter(Book.is_active == True)
    
    if grade_level:
        query = query.filter(Book.grade_level.ilike(grade_level))
    
    if query_str:
        query = query.filter(
            Book.title.ilike(f"%{query_str}%")
            | Book.publisher_code.ilike(f"%{query_str}%")
        )
    
    items = query.order_by(Book.grade_level, Book.title).limit(limit).all()
    total = query.count()
    
    return {"query": q, "items": [book.to_dict() for book in items], "total": total}


@router.get("/books/{book_id}")
def get_book(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Get a specific book by ID."""
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    
    return book.to_dict()
