from datetime import datetime, timezone
from typing import Annotated
from io import BytesIO
import re

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import String, func, or_
from sqlalchemy.orm import Session
import pandas as pd

from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import BookInventory, Student, User, UserRole, StudentStatus

router = APIRouter(tags=["students"])


def normalize_grade_level(value: object) -> str:
    grade = str(value).strip()
    numeric_grade = re.fullmatch(r"(?:grade\s*)?(\d+)(?:\.0+)?", grade, flags=re.IGNORECASE)
    return f"Grade {numeric_grade.group(1)}" if numeric_grade else grade


def adjust_grade_inventory(db: Session, grade: object, delta: int) -> None:
    """Add `delta` complete sets to every inventory category of the given grade.

    Called from the handoff / return endpoints so the book_inventories table
    stays in step with student actions. The change is flushed with the caller's
    transaction, so it commits (or rolls back) together with the student update.

    - Grades with no inventory rows are not tracked, so nothing changes.
    - Inventory can never fall below zero: a decrease that would do so raises
      409 and nothing is changed.
    """
    target = normalize_grade_level(grade)
    rows = [
        row
        for row in db.query(BookInventory).with_for_update().all()
        if normalize_grade_level(row.grade_level) == target
    ]
    if not rows:
        return

    if delta < 0:
        short = [row.category for row in rows if row.complete_set_count + delta < 0]
        if short:
            raise HTTPException(
                status_code=409,
                detail=f"Not enough inventory for {target}: out of stock for {', '.join(short)}",
            )

    for row in rows:
        row.complete_set_count += delta


@router.get("/students")
def list_students(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    query = db.query(Student).order_by(Student.full_name)
    
    # Volunteers only see their assigned grade
    if current_user.role == UserRole.VOLUNTEER.value and current_user.assigned_grade:
        query = query.filter(Student.registered_grade_level == current_user.assigned_grade)
    
    items = query.limit(limit).all()
    total = query.count()
    return {"items": [student.to_dict() for student in items], "total": total}


@router.get("/students/search")
def search_students(
    q: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    query_str = (q or "").strip()
    
    query = db.query(Student)
    
    # Volunteers only see their assigned grade
    if current_user.role == UserRole.VOLUNTEER.value and current_user.assigned_grade:
        query = query.filter(Student.registered_grade_level == current_user.assigned_grade)
    
    if query_str:
        # Search by name, student IDs, school, and grade
        query = query.filter(
            or_(
                Student.full_name.ilike(f"%{query_str}%"),
                Student.id.ilike(f"%{query_str}%"),
                Student.tts_student_id.cast(String).ilike(f"%{query_str}%"),
                Student.cta_student_id.cast(String).ilike(f"%{query_str}%"),
                Student.school.ilike(f"%{query_str}%"),
                Student.registered_grade_level.ilike(f"%{query_str}%"),
            )
        )
    
    items = query.order_by(Student.full_name).limit(limit).all()
    total = query.count()

    return {"query": q, "items": [student.to_dict() for student in items], "total": total}


@router.get("/students/status-summary")
def student_status_summary(
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    query = db.query(Student.status, func.count(Student.id)).group_by(Student.status)

    if current_user.role == UserRole.VOLUNTEER.value:
        if not current_user.assigned_grade:
            return {"total": 0, "counts": {}}
        query = query.filter(Student.registered_grade_level == current_user.assigned_grade)

    counts = {status: count for status, count in query.all()}
    return {
        "total": sum(counts.values()),
        "counts": {status.value: counts.get(status.value, 0) for status in StudentStatus},
    }


@router.get("/students/queue")
def student_queue(
    grade: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    query = db.query(Student)
    
    # Volunteers automatically get their assigned grade
    if current_user.role == UserRole.VOLUNTEER.value:
        if current_user.assigned_grade:
            grade = current_user.assigned_grade
        else:
            return {"grade": None, "status": status, "items": [], "message": "No grade assigned to volunteer"}
    
    if grade:
        query = query.filter(Student.registered_grade_level.ilike(grade))
    if status:
        query = query.filter(Student.status.ilike(status))

    # Order by status priority (APPROVED first for hand-over), then by name
    from sqlalchemy import case
    status_priority = case(
        (Student.status == 'APPROVED', 1),
        (Student.status == 'READY_FOR_PICKUP', 2),
        (Student.status == 'PENDING_SWAP', 3),
        else_=4
    )
    items = query.order_by(status_priority, Student.full_name).all()
    return {"grade": grade, "status": status, "items": [student.to_dict() for student in items]}


@router.post("/students/approve")
def approve_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    
    # Volunteers can only approve students in their assigned grade
    if current_user.role == UserRole.VOLUNTEER.value:
        if current_user.assigned_grade and student.registered_grade_level != current_user.assigned_grade:
            raise HTTPException(
                status_code=403,
                detail=f"You can only approve students in {current_user.assigned_grade}",
            )
    
    if student.status != StudentStatus.READY_FOR_PICKUP.value:
        raise HTTPException(status_code=400, detail=f"Student {student_id} is not eligible for approval")

    student.status = "APPROVED"
    student.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(student)
    return {"message": f"Student {student_id} approved for pickup", "student": student.to_dict()}


@router.post("/students/handoff")
def complete_handoff(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    
    # Volunteers can only handoff students in their assigned grade
    if current_user.role == UserRole.VOLUNTEER.value:
        if current_user.assigned_grade and student.registered_grade_level != current_user.assigned_grade:
            raise HTTPException(
                status_code=403,
                detail=f"You can only handoff students in {current_user.assigned_grade}",
            )
    
    if student.status != "APPROVED":
        raise HTTPException(status_code=400, detail=f"Student {student_id} is not approved for handoff")

    # Handover: one set leaves stock for the student's grade.
    adjust_grade_inventory(db, student.registered_grade_level, -1)

    student.status = "BOOK_HANDED_OVER"
    student.book_handed_over_at = datetime.now(timezone.utc)
    student.book_handed_over_grade = student.registered_grade_level
    db.commit()
    db.refresh(student)
    return {"message": f"Book handed over to {student_id}", "student": student.to_dict()}


@router.post("/students/return")
def accept_book_return(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    if current_user.role not in [UserRole.ADMIN.value, UserRole.BOOKS_TEAM_LEAD.value]:
        raise HTTPException(status_code=403, detail="Only admin or books team lead can accept returns")

    if student.status == StudentStatus.PENDING_SWAP.value:
        next_status = StudentStatus.READY_FOR_PICKUP.value
    elif student.status == StudentStatus.WITHDRAWN_BOOK_NOT_RETURNED.value:
        next_status = StudentStatus.WITHDRAWN_INACTIVE.value
    else:
        raise HTTPException(status_code=400, detail=f"Student {student_id} has no book pending return")

    # Return: the set comes back into stock for the grade it was issued for.
    # For a swap (PENDING_SWAP) that is the student's current/old grade; the
    # upgrade grade is reduced later, when the new book is handed over.
    returned_grade = student.book_handed_over_grade or student.registered_grade_level
    adjust_grade_inventory(db, returned_grade, +1)

    student.status = next_status
    student.pending_swap_flag = False
    student.book_returned_at = datetime.now(timezone.utc)
    student.book_handed_over_grade = None
    db.commit()
    db.refresh(student)
    return {"message": f"Book return accepted for {student_id}", "student": student.to_dict()}

@router.post("/students/upload")
async def upload_students(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Upload student roster from CSV or Excel file.
    Performs insert/update sync based on cta_student_id.

    Required columns:
    - cta_student_id: unique student ID from CTA
    - full_name: student full name
    - registered_grade_level: e.g., "Grade 6", "Grade 7"

    Optional columns:
    - school: school name
    - section: section name (e.g., 'A', 'B', 'Section 1')
    - parent_email / parent_email_id: parent contact email

    Business rule (per implementation spec, section 7.3):
    - If a student's grade changes AND they've already had a book handed over,
      they are flagged PENDING_SWAP instead of silently moving grade, so staff
      know to verify/reclaim the old book before issuing a new one.
    """
    # Only admin and books_team_lead can upload
    if current_user.role not in [UserRole.ADMIN.value, UserRole.BOOKS_TEAM_LEAD.value]:
        raise HTTPException(status_code=403, detail="Only admin and books team lead can upload students")

    # Validate file type
    filename = file.filename.lower()
    if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="File must be CSV or Excel (.csv, .xlsx, .xls)")

    try:
        # Read file content
        content = await file.read()

        # Parse based on file type
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        else:
            # For Excel/HTML files, try multiple parsers
            try:
                df = pd.read_excel(BytesIO(content))
            except Exception:
                # CTA exports .xls as HTML format
                df = pd.read_html(BytesIO(content))[0]

        # Remove completely blank rows
        df = df.dropna(how='all')

        # Normalize column names (lowercase, strip spaces)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

        # Detect column mappings (flexible naming)
        col_map = {}

        # Map cta_student_id
        for col in ['student_id', 'cta_student_id', 'id']:
            if col in df.columns:
                col_map['cta_student_id'] = col
                break

        # Map full_name (either combined or separate first/last)
        if 'full_name' in df.columns:
            col_map['full_name'] = 'full_name'
        elif 'student_first_name' in df.columns and 'student_last_name' in df.columns:
            df['full_name'] = df['student_first_name'].astype(str) + ' ' + df['student_last_name'].astype(str)
            col_map['full_name'] = 'full_name'
        elif 'first_name' in df.columns and 'last_name' in df.columns:
            df['full_name'] = df['first_name'].astype(str) + ' ' + df['last_name'].astype(str)
            col_map['full_name'] = 'full_name'

        # Map grade
        for col in ['registered_grade_level', 'grade_level', 'grade', 'grade_name']:
            if col in df.columns:
                col_map['registered_grade_level'] = col
                break

        # Map school (optional)
        for col in ['school', 'school_name']:
            if col in df.columns:
                col_map['school'] = col
                break

        # Map section (optional)
        for col in ['section', 'section_name', 'section_no']:
            if col in df.columns:
                col_map['section'] = col
                break

        # Map parent email (optional)
        for col in ['parent_email_id', 'parent_email', 'email']:
            if col in df.columns:
                col_map['parent_email'] = col
                break

        # Validate required mappings found
        required_fields = ['cta_student_id', 'full_name', 'registered_grade_level']
        missing_fields = [field for field in required_fields if field not in col_map]
        if missing_fields:
            available_cols = ', '.join(df.columns.tolist())
            raise HTTPException(
                status_code=400,
                detail=f"Could not find required columns. Missing: {', '.join(missing_fields)}. Available columns: {available_cols}"
            )

        # Track results
        inserted = 0
        updated = 0
        pending_swap_count = 0
        withdrawn_count = 0
        imported_cta_ids = set()
        errors = []

        # Get the current max tts_student_id for generating new IDs
        max_tts_id_result = db.query(Student.tts_student_id).order_by(Student.tts_student_id.desc()).first()
        next_tts_id = (max_tts_id_result[0] + 1) if max_tts_id_result and max_tts_id_result[0] else 1001

        # Process each row
        for idx, row in df.iterrows():
            try:
                # Get values using mapped column names
                cta_id = row[col_map['cta_student_id']]
                full_name = row[col_map['full_name']]
                grade = row[col_map['registered_grade_level']]

                if pd.isna(cta_id) or pd.isna(full_name) or pd.isna(grade):
                    errors.append(f"Row {idx + 2}: Missing required field(s)")
                    continue

                # Convert cta_student_id to integer
                try:
                    cta_id = int(cta_id)
                except (ValueError, TypeError):
                    errors.append(f"Row {idx + 2}: Invalid cta_student_id '{cta_id}' (must be numeric)")
                    continue

                imported_cta_ids.add(cta_id)
                new_grade = normalize_grade_level(grade)
                is_new_student = False

                # SAVEPOINT for this row only - so if ANYTHING below fails
                # (bad data, duplicate constraint, etc.), only THIS row's
                # changes are undone - not every row already flushed
                # successfully earlier in this same upload.
                savepoint = db.begin_nested()
                try:
                    # Check if student exists
                    existing = db.query(Student).filter(Student.cta_student_id == cta_id).first()

                    if existing:
                        # UPDATE: only update name, grade, school, section, email -
                        # preserve status/timestamps EXCEPT for the grade-change +
                        # already-handed-over case, which requires a PENDING_SWAP flag.
                        existing.full_name = str(full_name).strip()

                        grade_changed = normalize_grade_level(existing.registered_grade_level) != new_grade
                        already_handed_over = existing.status == StudentStatus.BOOK_HANDED_OVER.value

                        if grade_changed and already_handed_over:
                            # Per spec 7.3: grade changed after book already picked up ->
                            # PENDING_SWAP, blocked from new book until verified return.
                            # Keep the original handed-over grade as the grade the book was issued for.
                            previous_grade = existing.registered_grade_level.strip()
                            if existing.book_handed_over_grade is None:
                                existing.book_handed_over_grade = previous_grade
                            existing.registered_grade_level = new_grade
                            existing.status = StudentStatus.PENDING_SWAP.value
                            existing.pending_swap_flag = True
                            pending_swap_count += 1
                        else:
                            existing.registered_grade_level = new_grade

                        if 'school' in col_map and not pd.isna(row.get(col_map['school'])):
                            existing.school = str(row[col_map['school']]).strip()
                        if 'section' in col_map and not pd.isna(row.get(col_map['section'])):
                            existing.section = str(row[col_map['section']]).strip()
                        if 'parent_email' in col_map and not pd.isna(row.get(col_map['parent_email'])):
                            existing.parent_email = str(row[col_map['parent_email']]).strip()
                    else:
                        # INSERT: create new student
                        student_id = f"TTS-{next_tts_id}"

                        school_value = 'Unknown'
                        if 'school' in col_map and not pd.isna(row.get(col_map['school'])):
                            school_value = str(row[col_map['school']]).strip()

                        section_value = None
                        if 'section' in col_map and not pd.isna(row.get(col_map['section'])):
                            section_value = str(row[col_map['section']]).strip()

                        parent_email_value = None
                        if 'parent_email' in col_map and not pd.isna(row.get(col_map['parent_email'])):
                            parent_email_value = str(row[col_map['parent_email']]).strip()

                        new_student = Student(
                            id=student_id,
                            tts_student_id=next_tts_id,
                            cta_student_id=cta_id,
                            full_name=str(full_name).strip(),
                            registered_grade_level=new_grade,
                            school=school_value,
                            section=section_value,
                            parent_email=parent_email_value,
                            status=StudentStatus.READY_FOR_PICKUP.value,
                        )
                        db.add(new_student)
                        is_new_student = True
                        next_tts_id += 1  # Increment for next new student

                    # Flush within the savepoint - surfaces constraint violations
                    # (e.g. duplicate cta_student_id within this same file) here,
                    # so we can roll back just this row instead of the whole batch.
                    db.flush()
                    savepoint.commit()  # releases the savepoint, outer txn stays open

                    if is_new_student:
                        inserted += 1
                    else:
                        updated += 1

                except Exception as row_error:
                    savepoint.rollback()  # undoes only this row's changes
                    errors.append(f"Row {idx + 2}: {str(row_error)}")
                    continue

            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
                continue

        # Any current student absent from this upload is treated as withdrawn.
        # This keeps the roster in sync with the latest external report while
        # preserving historical data for students already marked inactive.
        if imported_cta_ids:
            missing_students = db.query(Student).filter(~Student.cta_student_id.in_(list(imported_cta_ids))).all()
        else:
            missing_students = db.query(Student).all()

        for student in missing_students:
            if student.status in {
                StudentStatus.WITHDRAWN_INACTIVE.value,
                StudentStatus.WITHDRAWN_BOOK_NOT_RETURNED.value,
            }:
                continue

            if student.status in {
                StudentStatus.BOOK_HANDED_OVER.value,
                StudentStatus.CLAIMED.value,
            }:
                student.status = StudentStatus.WITHDRAWN_BOOK_NOT_RETURNED.value
            else:
                student.status = StudentStatus.WITHDRAWN_INACTIVE.value

            student.pending_swap_flag = False
            student.is_active = False
            withdrawn_count += 1

        # Commit all changes
        db.commit()

        return {
            "message": "Upload completed",
            "summary": {
                "total_rows": len(df),
                "inserted": inserted,
                "updated": updated,
                "pending_swap_flagged": pending_swap_count,
                "withdrawn": withdrawn_count,
                "errors": len(errors),
            },
            "error_details": errors[:50] if errors else [],  # Return first 50 errors
        }

    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="File is empty")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")
