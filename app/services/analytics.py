import sqlite3

from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.core.config import get_settings


settings = get_settings()


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():

    db_path = Path(settings.audit_db_path)

    con = sqlite3.connect(
        str(db_path),
        timeout=10
    )

    con.row_factory = sqlite3.Row

    return con


# --------------------------------------------------
# ANALYTICS SUMMARY
# --------------------------------------------------

def get_analytics_summary():

    con = get_connection()

    try:

        today = datetime.now(timezone.utc).date().isoformat()

        # Total queries and status
        overview = con.execute(
            """
            SELECT

                COUNT(*) AS total_queries,

                SUM(
                    CASE WHEN status = 'success'
                    THEN 1 ELSE 0 END
                ) AS successful_queries,

                SUM(
                    CASE WHEN status = 'failed'
                    THEN 1 ELSE 0 END
                ) AS failed_queries,

                SUM(
                    CASE WHEN DATE(created_at) = ?
                    THEN 1 ELSE 0 END
                ) AS today_queries,

                AVG(response_time_ms) AS avg_response_time,

                SUM(retry_count) AS total_retries

            FROM query_audit
            """,
            (today,)
        ).fetchone()

        # Source distribution
        sources = con.execute(
            """
            SELECT
                source_used,
                COUNT(*) AS total

            FROM query_audit

            GROUP BY source_used
            """
        ).fetchall()

        source_distribution = {
            row["source_used"]: row["total"]
            for row in sources
        }

        total = overview["total_queries"] or 0

        successful = overview["successful_queries"] or 0

        success_rate = (
            round((successful / total) * 100, 2)
            if total > 0 else 0
        )

        return {

            "total_queries": total,

            "today_queries": overview["today_queries"] or 0,

            "successful_queries": successful,

            "failed_queries": overview["failed_queries"] or 0,

            "success_rate": success_rate,

            "average_response_time_ms": round(
                overview["avg_response_time"] or 0,
                2
            ),

            "total_retries": overview["total_retries"] or 0,

            "source_distribution": {
                "private_kb": source_distribution.get("private_kb", 0),
                "web_search": source_distribution.get("web_search", 0),
                "direct": source_distribution.get("direct", 0),
                "insufficient_evidence": source_distribution.get(
                    "insufficient_evidence", 0
                )
            }
        }

    finally:

        con.close()


# --------------------------------------------------
# DAILY QUERY ANALYTICS
# --------------------------------------------------

def get_daily_analytics(days: int = 7):

    days = max(1, min(days, 365))

    con = get_connection()

    try:

        start_date = (
            datetime.now(timezone.utc).date()
            - timedelta(days=days - 1)
        ).isoformat()

        rows = con.execute(
            """
            SELECT

                DATE(created_at) AS date,

                COUNT(*) AS total_queries,

                SUM(
                    CASE WHEN status = 'success'
                    THEN 1 ELSE 0 END
                ) AS successful_queries,

                SUM(
                    CASE WHEN status = 'failed'
                    THEN 1 ELSE 0 END
                ) AS failed_queries

            FROM query_audit

            WHERE DATE(created_at) >= ?

            GROUP BY DATE(created_at)

            ORDER BY date ASC
            """,
            (start_date,)
        ).fetchall()

        return [
            {
                "date": row["date"],
                "total_queries": row["total_queries"],
                "successful_queries": row["successful_queries"] or 0,
                "failed_queries": row["failed_queries"] or 0
            }
            for row in rows
        ]

    finally:

        con.close()


# --------------------------------------------------
# RECENT ACTIVITY
# --------------------------------------------------

def get_recent_activity(limit: int = 10):

    limit = max(1, min(limit, 100))

    con = get_connection()

    try:

        rows = con.execute(
            """
            SELECT

                id,
                created_at,
                question,
                source_used,
                status,
                response_time_ms,
                retry_count

            FROM query_audit

            ORDER BY id DESC

            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        con.close()


# --------------------------------------------------
# COMPLETE ANALYTICS DATA
# --------------------------------------------------

def get_complete_analytics(days: int = 7):

    return {

        "overview": get_analytics_summary(),

        "daily_analytics": get_daily_analytics(days),

        "recent_activity": get_recent_activity(10)

    }