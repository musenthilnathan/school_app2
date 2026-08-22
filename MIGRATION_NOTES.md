# Student Model Enhancement - Migration Notes

## Date: 2026-08-22

## Summary
Enhanced the Student model to fully match the TTS_BDS implementation design specification with dual student ID tracking, flags, and audit timestamps.

## Changes Made

### 1. **New Student Model Fields**
- `tts_student_id` (BigInteger) - Internal immutable numeric ID for fast lookups
- `cta_student_id` (BigInteger) - External CTA-assigned student ID (source of truth)
- `pending_swap_flag` (Boolean) - Indicates student needs book swap
- `approved_at` (DateTime) - Timestamp when student was approved for pickup
- `book_handed_over_at` (DateTime) - Timestamp when book was handed over
- `last_uploaded_batch_id` (String) - Tracks which import batch last updated this student

### 2. **Renamed Fields (for consistency with spec)**
- `name` → `full_name`
- `grade` → `registered_grade_level`

### 3. **New Enum: StudentStatus**
Added type-safe enum for student statuses:
- `READY_FOR_PICKUP`
- `APPROVED`
- `BOOK_HANDED_OVER`
- `WITHDRAWN_INACTIVE`
- `PENDING_SWAP`
- `BACKORDERED`
- `CLAIMED`

### 4. **Updated API Endpoints**
- Enhanced student search to include `tts_student_id` and `cta_student_id` searching
- Timestamp fields are now set automatically on approve/handoff actions
- API responses maintain backward compatibility (include both `name`/`full_name` and `grade`/`registered_grade_level`)

### 5. **Seed Data Updated**
All sample students now include:
- Both student ID types
- Proper flag values
- Realistic status combinations

## Migration Steps

### Option 1: Reset Development Database (Recommended for Dev)
```bash
cd backend

# Make sure venv is activated
source ../.venv/bin/activate

# Run the reset script
python reset_db.py
```

### Option 2: Manual PostgreSQL Migration (if you have existing data to preserve)
```sql
-- Add new columns
ALTER TABLE students ADD COLUMN tts_student_id BIGINT;
ALTER TABLE students ADD COLUMN cta_student_id BIGINT;
ALTER TABLE students ADD COLUMN pending_swap_flag BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE students ADD COLUMN approved_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE students ADD COLUMN book_handed_over_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE students ADD COLUMN last_uploaded_batch_id VARCHAR(64);

-- Rename columns
ALTER TABLE students RENAME COLUMN name TO full_name;
ALTER TABLE students RENAME COLUMN grade TO registered_grade_level;

-- Populate IDs for existing records (adjust as needed for your data)
-- This is an example - you'll need to map your existing data appropriately
UPDATE students SET 
  tts_student_id = 1000 + ROW_NUMBER() OVER (ORDER BY created_at),
  cta_student_id = 50000 + ROW_NUMBER() OVER (ORDER BY created_at)
WHERE tts_student_id IS NULL;

-- Add constraints
ALTER TABLE students ALTER COLUMN tts_student_id SET NOT NULL;
ALTER TABLE students ALTER COLUMN cta_student_id SET NOT NULL;
ALTER TABLE students ADD CONSTRAINT students_tts_student_id_unique UNIQUE (tts_student_id);
ALTER TABLE students ADD CONSTRAINT students_cta_student_id_unique UNIQUE (cta_student_id);
CREATE INDEX idx_students_tts_student_id ON students(tts_student_id);
CREATE INDEX idx_students_cta_student_id ON students(cta_student_id);
CREATE INDEX idx_students_full_name ON students(full_name);
CREATE INDEX idx_students_registered_grade_level ON students(registered_grade_level);
```

## Testing
All 15 existing tests continue to pass with the new schema.

```bash
cd backend
pytest -v
```

## Next Steps
With the enhanced Student model complete, you can now proceed to:
1. **Book Catalog & Inventory Management** - Track books and stock levels
2. **CSV/Excel Student Roster Import** - Bulk upload student data
3. **Distribution Queue Model** - Separate queue management
4. **Audit Logging** - Full event tracking

## Backward Compatibility
The API maintains backward compatibility by including both old and new field names:
- `name` (kept for compatibility) + `full_name` (new spec name)
- `grade` (kept for compatibility) + `registered_grade_level` (new spec name)

Frontend code can be gradually updated to use the new field names.
