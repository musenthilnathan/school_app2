from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import Inventory, User, UserRole

router = APIRouter(tags=["inventory"])


class InventoryUpdateRequest(BaseModel):
    actual_quantity: int | None = None
    rollover_stock: int | None = None
    spare_stock: int | None = None


@router.get("/inventory")
def list_inventory(
    academic_year: str = "2024-2025",
    grade_level: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """List inventory records for the given academic year."""
    query = db.query(Inventory).filter(Inventory.academic_year == academic_year)
    
    if grade_level:
        query = query.join(Inventory.book).filter(Inventory.book.has(grade_level=grade_level))
    
    items = query.order_by(Inventory.id).limit(limit).all()
    total = query.count()
    
    return {"items": [inv.to_dict() for inv in items], "total": total, "academic_year": academic_year}


@router.get("/inventory/{inventory_id}")
def get_inventory(
    inventory_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Get a specific inventory record."""
    inventory = db.get(Inventory, inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail=f"Inventory {inventory_id} not found")
    
    return inventory.to_dict()


@router.patch("/inventory/{inventory_id}")
def update_inventory(
    inventory_id: str,
    updates: InventoryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Update inventory quantities. Books Team Lead only."""
    # Only Books Team Lead and Admin can update inventory
    if current_user.role not in [UserRole.BOOKS_TEAM_LEAD.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=403,
            detail="Only Books Team Lead or Admin can update inventory",
        )
    
    inventory = db.get(Inventory, inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail=f"Inventory {inventory_id} not found")
    
    # Apply updates
    if updates.actual_quantity is not None:
        inventory.actual_quantity = updates.actual_quantity
    if updates.rollover_stock is not None:
        inventory.rollover_stock = updates.rollover_stock
    if updates.spare_stock is not None:
        inventory.spare_stock = updates.spare_stock
    
    # Recalculate projected inventory
    inventory.update_projected_inventory()
    
    db.commit()
    db.refresh(inventory)
    
    return {
        "message": f"Inventory {inventory_id} updated",
        "inventory": inventory.to_dict(),
    }


@router.get("/inventory/summary/{academic_year}")
def inventory_summary(
    academic_year: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Get inventory summary by grade level."""
    inventories = db.query(Inventory).filter(Inventory.academic_year == academic_year).all()
    
    # Group by grade level
    summary = {}
    for inv in inventories:
        grade = inv.book.grade_level
        if grade not in summary:
            summary[grade] = {
                "grade_level": grade,
                "total_expected": 0,
                "total_actual": 0,
                "total_projected": 0,
                "discrepancy": 0,
            }
        
        summary[grade]["total_expected"] += inv.expected_quantity
        summary[grade]["total_actual"] += inv.actual_quantity
        summary[grade]["total_projected"] += inv.projected_available_inventory
        summary[grade]["discrepancy"] += (inv.expected_quantity - inv.actual_quantity)
    
    return {
        "academic_year": academic_year,
        "summary": list(summary.values()),
    }
