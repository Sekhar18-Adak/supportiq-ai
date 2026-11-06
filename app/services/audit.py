import json
import sqlite3

from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from app.core.config import get_settings


settings = get_settings()


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():

    db_path = Path(settings.audit_db_path)

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    return sqlite3.connect(
        str(db_path),
        timeout=10
    )


# --------------------------------------------------
# DATABASE INITIALIZATION + MIGRATION
# --------------------------------------------------

def init_db() -> None:

    con = get_connection()

    try:

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS query_audit (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                created_at TEXT NOT NULL,

                question TEXT NOT NULL,

                source_used TEXT NOT NULL,

                trace_json TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'success',

                response_time_ms REAL,

                retry_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        # Check existing table columns
        existing_columns = {
            row[1]
            for row in con.execute(
                "PRAGMA table_info(query_audit)"
            ).fetchall()
        }

        # Safely add missing columns
        migrations = {

            "status": """
                ALTER TABLE query_audit
                ADD COLUMN status TEXT NOT NULL DEFAULT 'success'
            """,

            "response_time_ms": """
                ALTER TABLE query_audit
                ADD COLUMN response_time_ms REAL
            """,

            "retry_count": """
                ALTER TABLE query_audit
                ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0
            """
        }

        for column, sql in migrations.items():

            if column not in existing_columns:

                con.execute(sql)

        con.commit()

    finally:

        con.close()


# --------------------------------------------------
# WRITE AUDIT LOG
# --------------------------------------------------

def write_audit(
    question: str,
    source_used: str,
    trace: list,
    status: str = "success",
    response_time_ms: Optional[float] = None,
    retry_count: int = 0
) -> None:

    con = get_connection()

    try:

        con.execute(
            """
            INSERT INTO query_audit (
                created_at,
                question,
                source_used,
                trace_json,
                status,
                response_time_ms,
                retry_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,

            (
                datetime.now(timezone.utc).isoformat(),
                question,
                source_used,
                json.dumps(trace),
                status,
                response_time_ms,
                retry_count
            )
        )

        con.commit()

    finally:

        con.close()