from datetime import datetime, timezone
from typing import Annotated
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import String, or_
from sqlalchemy.orm import Session
import pandas as pd

from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import Student, User, UserRole, StudentStatus

router = APIRouter(tags=["students"])


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
    
    if student.status not in {"READY_FOR_PICKUP", "PENDING_SWAP"}:
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

    student.status = "BOOK_HANDED_OVER"
    student.book_handed_over_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(student)
    return {"message": f"Book handed over to {student_id}", "student": student.to_dict()}


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
            except:
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
            # Combine first and last name
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
                
                # Check if student exists
                existing = db.query(Student).filter(Student.cta_student_id == cta_id).first()
                
                if existing:
                    # UPDATE: only update name, grade, school, section - preserve status and timestamps
                    existing.full_name = str(full_name).strip()
                    existing.registered_grade_level = str(grade).strip()
                    if 'school' in col_map and not pd.isna(row.get(col_map['school'])):
                        existing.school = str(row[col_map['school']]).strip()
                    if 'section' in col_map and not pd.isna(row.get(col_map['section'])):
                        existing.section = str(row[col_map['section']]).strip()
                    if 'parent_email' in col_map and not pd.isna(row.get(col_map['parent_email'])):
                        existing.parent_email = str(row[col_map['parent_email']]).strip()
                    updated += 1
                else:
                    # INSERT: create new student
                    # Generate ID in TTS-XXXX format
                    student_id = f"TTS-{next_tts_id}"
                    
                    # Get school value
                    school_value = 'Unknown'
                    if 'school' in col_map and not pd.isna(row.get(col_map['school'])):
                        school_value = str(row[col_map['school']]).strip()
                    
                    # Get section value (optional)
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
                        registered_grade_level=str(grade).strip(),
                        school=school_value,
                        section=section_value,
                        parent_email=parent_email_value,
                        status=StudentStatus.READY_FOR_PICKUP.value,
                    )
                    db.add(new_student)
                    inserted += 1
                    next_tts_id += 1  # Increment for next new student
                    
            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
                continue
        
        # Commit all changes
        db.commit()
        
        return {
            "message": "Upload completed",
            "summary": {
                "total_rows": len(df),
                "inserted": inserted,
                "updated": updated,
                "errors": len(errors),
            },
            "error_details": errors[:50] if errors else [],  # Return first 50 errors
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="File is empty")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")
