from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UserRole(str, Enum):
    BOOKS_TEAM_LEAD = "books_team_lead"
    VOLUNTEER = "volunteer"
    ADMIN = "admin"


class StudentStatus(str, Enum):
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    APPROVED = "APPROVED"
    BOOK_HANDED_OVER = "BOOK_HANDED_OVER"
    WITHDRAWN_INACTIVE = "WITHDRAWN_INACTIVE"
    PENDING_SWAP = "PENDING_SWAP"
    BACKORDERED = "BACKORDERED"
    CLAIMED = "CLAIMED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "assigned_grade": self.assigned_grade,
            "is_active": self.is_active,
        }


class Student(Base):
    __tablename__ = "students"

    # Primary key (UUID for internal use)
    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    
    # Student identifiers (per design spec)
    tts_student_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    cta_student_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    
    # Student information
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    school: Mapped[str] = mapped_column(String(255), nullable=False)
    registered_grade_level: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(50), nullable=True)  # e.g., 'A', 'B', 'Section 1'
    
    # Status and flags
    status: Mapped[str] = mapped_column(
        String(64), 
        nullable=False, 
        default=StudentStatus.READY_FOR_PICKUP.value
    )
    pending_swap_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Event timestamps
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    book_handed_over_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Import tracking
    last_uploaded_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tts_student_id": self.tts_student_id,
            "cta_student_id": self.cta_student_id,
            "name": self.full_name,  # Keep 'name' in API for backward compatibility
            "full_name": self.full_name,
            "school": self.school,
            "grade": self.registered_grade_level,  # Keep 'grade' for backward compatibility
            "registered_grade_level": self.registered_grade_level,
            "section": self.section,
            "status": self.status,
            "pending_swap_flag": self.pending_swap_flag,
            "is_active": self.is_active,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "book_handed_over_at": self.book_handed_over_at.isoformat() if self.book_handed_over_at else None,
        }


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    publisher_code: Mapped[str] = mapped_column(String(100), nullable=False)
    grade_level: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    base_unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to inventories
    inventories: Mapped[list["Inventory"]] = relationship("Inventory", back_populates="book")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "publisher_code": self.publisher_code,
            "grade_level": self.grade_level,
            "base_unit_cost": float(self.base_unit_cost),
            "is_active": self.is_active,
        }


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    academic_year: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    book_id: Mapped[str] = mapped_column(String(64), ForeignKey("books.id"), nullable=False, index=True)
    
    # Quantities
    expected_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rollover_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spare_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Costs
    invoice_shipping_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    
    # Computed field (can be calculated or stored)
    projected_available_inventory: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to book
    book: Mapped["Book"] = relationship("Book", back_populates="inventories")

    def to_dict(self):
        return {
            "id": self.id,
            "academic_year": self.academic_year,
            "book_id": self.book_id,
            "book": self.book.to_dict() if self.book else None,
            "expected_quantity": self.expected_quantity,
            "actual_quantity": self.actual_quantity,
            "rollover_stock": self.rollover_stock,
            "spare_stock": self.spare_stock,
            "invoice_shipping_cost": float(self.invoice_shipping_cost),
            "projected_available_inventory": self.projected_available_inventory,
        }
    
    def calculate_projected_inventory(self) -> int:
        """Calculate projected available inventory based on actual + rollover + spare."""
        return self.actual_quantity + self.rollover_stock + self.spare_stock
    
    def update_projected_inventory(self):
        """Update the projected_available_inventory field."""
        self.projected_available_inventory = self.calculate_projected_inventory()

