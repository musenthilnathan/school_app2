from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import BookInventory, User, UserRole

router = APIRouter(tags=["book-inventories"])


class BookInventoryUpdate(BaseModel):
    complete_set_count: int | None = Field(default=None, ge=0)
    extra_count: int | None = Field(default=None, ge=0)


@router.get("/book-inventories")
def list_book_inventories(
    grade_level: str | None = None,
    q: str = "",
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List book inventory rows, optionally filtered by grade level and/or category text."""
    query = db.query(BookInventory)
    if grade_level:
        query = query.filter(BookInventory.grade_level == grade_level)
    if q.strip():
        query = query.filter(BookInventory.category.ilike(f"%{q.strip()}%"))

    items = query.order_by(BookInventory.id).all()
    grades = [g for (g,) in db.query(BookInventory.grade_level).order_by(BookInventory.id).all()]
    return {
        "items": [item.to_dict() for item in items],
        "total": len(items),
        "grade_levels": list(dict.fromkeys(grades)),  # unique, worksheet order
        "total_complete_sets": sum(i.complete_set_count for i in items),
        "total_extra": sum(i.extra_count for i in items),
    }


@router.patch("/book-inventories/{item_id}")
def update_book_inventory(
    item_id: int,
    updates: BookInventoryUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Update counts. Books Team Lead or Admin only."""
    if current_user.role not in (UserRole.BOOKS_TEAM_LEAD.value, UserRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="Only Books Team Lead or Admin can update inventory")

    item = db.get(BookInventory, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Book inventory {item_id} not found")

    if updates.complete_set_count is not None:
        item.complete_set_count = updates.complete_set_count
    if updates.extra_count is not None:
        item.extra_count = updates.extra_count

    db.commit()
    db.refresh(item)
    return item.to_dict()
