#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$REPO_ROOT/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
SQL_OUTFILE="$BACKUP_DIR/tts_bds_db_backup_${TIMESTAMP}.sql"
XLSX_OUTFILE="$BACKUP_DIR/students_export_${TIMESTAMP}.xlsx"

if command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker-compose)
elif docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker compose)
else
  echo "ERROR: docker-compose or docker compose is required but not found." >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx 'tts_bds_db'; then
  echo "==> Postgres container not running. Starting db..."
  if [[ "${DOCKER_COMPOSE[0]}" == "docker" ]]; then
    docker compose -f "$REPO_ROOT/docker-compose.yml" up -d db
  else
    docker-compose -f "$REPO_ROOT/docker-compose.yml" up -d db
  fi
fi

echo "==> Waiting for Postgres to become healthy..."
for i in $(seq 1 30); do
  STATUS="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}starting{{end}}' tts_bds_db 2>/dev/null || echo 'starting')"
  if [[ "$STATUS" == "healthy" ]]; then
    break
  fi
  sleep 1
done

if ! docker ps --format '{{.Names}}' | grep -qx 'tts_bds_db'; then
  echo "ERROR: Unable to start Postgres container 'tts_bds_db'." >&2
  exit 1
fi

echo "==> Creating SQL dump..."
if [[ "${DOCKER_COMPOSE[0]}" == "docker" ]]; then
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db pg_dump -U postgres -d tts_bds > "$SQL_OUTFILE"
else
  docker-compose -f "$REPO_ROOT/docker-compose.yml" exec -T db pg_dump -U postgres -d tts_bds > "$SQL_OUTFILE"
fi

if [[ ! -s "$SQL_OUTFILE" ]]; then
  echo "ERROR: Backup file was not created or is empty: $SQL_OUTFILE" >&2
  exit 1
fi

PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "ERROR: Project virtualenv not found at $PYTHON_BIN" >&2
  exit 1
fi

"$PYTHON_BIN" - "$XLSX_OUTFILE" <<'PY'
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


def normalize_datetime(value):
    if pd.isna(value):
        return value
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            value = value.tz_convert('UTC').tz_localize(None)
        return value.to_pydatetime()
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    return value

out_path = Path(sys.argv[1])
engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5432/tts_bds")

with engine.connect() as conn:
    summary_by_grade = pd.read_sql(
        text("""
            SELECT
                registered_grade_level AS grade,
                COUNT(*) AS total_students,
                SUM(CASE WHEN status = 'READY_FOR_PICKUP' THEN 1 ELSE 0 END) AS ready_for_pickup,
                SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN status = 'BOOK_HANDED_OVER' THEN 1 ELSE 0 END) AS book_handed_over,
                SUM(CASE WHEN status = 'WITHDRAWN_INACTIVE' THEN 1 ELSE 0 END) AS withdrawn_inactive,
                SUM(CASE WHEN status = 'WITHDRAWN_BOOK_NOT_RETURNED' THEN 1 ELSE 0 END) AS withdrawn_book_not_returned,
                SUM(CASE WHEN status = 'PENDING_SWAP' THEN 1 ELSE 0 END) AS pending_swap,
                SUM(CASE WHEN status = 'BACKORDERED' THEN 1 ELSE 0 END) AS backordered,
                SUM(CASE WHEN status = 'CLAIMED' THEN 1 ELSE 0 END) AS claimed
            FROM students
            GROUP BY registered_grade_level
            ORDER BY registered_grade_level
        """),
        conn,
    )
    summary_totals = pd.read_sql(
        text("""
            SELECT
                COUNT(*) AS total_students,
                SUM(CASE WHEN status = 'READY_FOR_PICKUP' THEN 1 ELSE 0 END) AS ready_for_pickup,
                SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN status = 'BOOK_HANDED_OVER' THEN 1 ELSE 0 END) AS book_handed_over,
                SUM(CASE WHEN status = 'WITHDRAWN_INACTIVE' THEN 1 ELSE 0 END) AS withdrawn_inactive,
                SUM(CASE WHEN status = 'WITHDRAWN_BOOK_NOT_RETURNED' THEN 1 ELSE 0 END) AS withdrawn_book_not_returned,
                SUM(CASE WHEN status = 'PENDING_SWAP' THEN 1 ELSE 0 END) AS pending_swap,
                SUM(CASE WHEN status = 'BACKORDERED' THEN 1 ELSE 0 END) AS backordered,
                SUM(CASE WHEN status = 'CLAIMED' THEN 1 ELSE 0 END) AS claimed
            FROM students
        """),
        conn,
    )
    students_df = pd.read_sql(
        text("SELECT * FROM students ORDER BY registered_grade_level, full_name"),
        conn,
    )

for column in students_df.columns:
    if pd.api.types.is_datetime64_any_dtype(students_df[column]) or students_df[column].map(lambda v: isinstance(v, (pd.Timestamp, datetime)) and getattr(v, 'tzinfo', None) is not None).any():
        students_df[column] = students_df[column].map(normalize_datetime)

if summary_by_grade.empty:
    summary_by_grade = pd.DataFrame([
        {
            "grade": "NO DATA",
            "total_students": 0,
            "ready_for_pickup": 0,
            "approved": 0,
            "book_handed_over": 0,
            "withdrawn_inactive": 0,
            "withdrawn_book_not_returned": 0,
            "pending_swap": 0,
            "backordered": 0,
            "claimed": 0,
        }
    ])

if summary_totals.empty:
    summary_totals = pd.DataFrame([
        {
            "total_students": 0,
            "ready_for_pickup": 0,
            "approved": 0,
            "book_handed_over": 0,
            "withdrawn_inactive": 0,
            "withdrawn_book_not_returned": 0,
            "pending_swap": 0,
            "backordered": 0,
            "claimed": 0,
        }
    ])

with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
    summary_header = [
        "grade",
        "total_students",
        "ready_for_pickup",
        "approved",
        "book_handed_over",
        "withdrawn_inactive",
        "withdrawn_book_not_returned",
        "pending_swap",
        "backordered",
        "claimed",
    ]

    pd.DataFrame([["Students Status Summary"]]).to_excel(writer, sheet_name="Summary", index=False, header=False, startrow=0)
    pd.DataFrame([summary_header]).to_excel(writer, sheet_name="Summary", index=False, header=False, startrow=2)
    summary_by_grade[summary_header].to_excel(writer, sheet_name="Summary", index=False, header=False, startrow=3)

    next_row = 3 + len(summary_by_grade) + 3
    pd.DataFrame([[""], ["Overall Totals"]]).to_excel(writer, sheet_name="Summary", index=False, header=False, startrow=next_row)
    overall_row = [int(summary_totals.iloc[0][col]) for col in summary_header[1:]]
    pd.DataFrame([overall_row], columns=summary_header[1:]).to_excel(
        writer,
        sheet_name="Summary",
        index=False,
        header=True,
        startrow=next_row + 2,
    )

    students_df.to_excel(writer, sheet_name="Students Data", index=False)

print(f"Student export created successfully: {out_path}")
PY

if [[ -s "$SQL_OUTFILE" && -s "$XLSX_OUTFILE" ]]; then
  echo "Backup created successfully: $SQL_OUTFILE"
  echo "Student export created successfully: $XLSX_OUTFILE"
  ls -lh "$SQL_OUTFILE" "$XLSX_OUTFILE"
else
  echo "ERROR: Could not validate the SQL backup or Excel export file." >&2
  exit 1
fi
