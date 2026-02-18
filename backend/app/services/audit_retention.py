"""Retention purge for the triple audit logging system.

Deletes expired events from all three stores (SQLite, JSONL files, PostgreSQL)
based on the event category:

* MUTATION  -- never deleted
* READ_ACCESS -- deleted after 90 days
* SYSTEM -- deleted after 30 days
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.services.audit_service import AuditEventCategory

logger = logging.getLogger(__name__)

# Retention windows (days).  None = never purge.
RETENTION_DAYS: dict[AuditEventCategory, int | None] = {
    AuditEventCategory.MUTATION: None,
    AuditEventCategory.READ_ACCESS: 90,
    AuditEventCategory.SYSTEM: 30,
}


async def purge_audit_retention(
    audit_base_path: str,
    pg_session_factory: Any,
) -> dict[str, int]:
    """Purge expired audit events from all three stores.

    Parameters
    ----------
    audit_base_path:
        Root directory for JSONL + SQLite (e.g. ``/app/audit_storage``).
    pg_session_factory:
        An ``async_sessionmaker`` or callable that returns an ``AsyncSession``
        context manager (e.g. ``AsyncSessionLocal``).

    Returns a summary dict of rows/lines removed.
    """
    base = Path(audit_base_path)
    now = datetime.now(timezone.utc)
    summary: dict[str, int] = {
        "sqlite_deleted": 0,
        "jsonl_lines_removed": 0,
        "pg_deleted": 0,
    }

    # ---- 1. SQLite purge ----
    sqlite_path = base / "audit.db"
    if sqlite_path.exists():
        conn = sqlite3.connect(str(sqlite_path))
        try:
            for category, days in RETENTION_DAYS.items():
                if days is None:
                    continue
                cutoff = (now - timedelta(days=days)).isoformat()
                cursor = conn.execute(
                    "DELETE FROM audit_events "
                    "WHERE category = ? AND timestamp < ?",
                    (category.value, cutoff),
                )
                summary["sqlite_deleted"] += cursor.rowcount
            conn.commit()
        finally:
            conn.close()

    # ---- 2. JSONL purge ----
    jsonl_dir = base / "jsonl"
    if jsonl_dir.exists():
        for jsonl_file in sorted(jsonl_dir.glob("*.jsonl")):
            file_date_str = jsonl_file.stem  # YYYY-MM-DD
            try:
                file_date = datetime.strptime(
                    file_date_str, "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            age_days = (now - file_date).days

            # Skip recent files (nothing to purge)
            if age_days < 30:
                continue

            # Read and filter lines
            lines_to_keep: list[str] = []
            lines_removed = 0

            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        cat_str = record.get("category", "mutation")
                        cat = AuditEventCategory(cat_str)
                        retention = RETENTION_DAYS.get(cat)
                        if retention is not None and age_days >= retention:
                            lines_removed += 1
                        else:
                            lines_to_keep.append(line)
                    except (json.JSONDecodeError, ValueError):
                        # Keep malformed lines (don't lose data)
                        lines_to_keep.append(line)

            if lines_removed > 0:
                summary["jsonl_lines_removed"] += lines_removed
                if lines_to_keep:
                    # Atomic rewrite via temp file
                    tmp = jsonl_file.with_suffix(".tmp")
                    with open(tmp, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines_to_keep) + "\n")
                    tmp.replace(jsonl_file)
                else:
                    jsonl_file.unlink()

    # ---- 3. PostgreSQL purge ----
    try:
        from sqlalchemy import text

        async with pg_session_factory() as db:
            for category, days in RETENTION_DAYS.items():
                if days is None:
                    continue
                cutoff = now - timedelta(days=days)
                result = await db.execute(
                    text(
                        "DELETE FROM audit_log "
                        "WHERE event_category = :category "
                        "AND created_at < :cutoff"
                    ),
                    {"category": category.value, "cutoff": cutoff},
                )
                summary["pg_deleted"] += result.rowcount
            await db.commit()
    except Exception:
        logger.exception("PostgreSQL audit purge failed")

    return summary
