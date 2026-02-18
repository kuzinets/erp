"""Triple-write audit logging service.

Provides fire-and-forget writes to JSONL files and SQLite, complementing
the primary PostgreSQL ``audit_log`` table.  Each event is categorised for
tiered retention:

* **MUTATION** -- kept forever (create, update, delete, login, etc.)
* **READ_ACCESS** -- purged after 90 days (report views, sensitive GETs)
* **SYSTEM** -- purged after 30 days (scheduler runs, startup, errors)

The ``TripleAuditWriter`` is designed as a singleton initialised once at
startup.  The ``fire_and_forget`` method schedules the I/O on the default
thread-pool so the calling async endpoint returns immediately.
"""

from __future__ import annotations

import asyncio
import dataclasses
import enum
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event category enum (drives retention policy)
# ---------------------------------------------------------------------------


class AuditEventCategory(str, enum.Enum):
    MUTATION = "mutation"  # Never deleted
    READ_ACCESS = "read_access"  # 90-day retention
    SYSTEM = "system"  # 30-day retention


# ---------------------------------------------------------------------------
# Canonical audit event
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AuditEvent:
    id: UUID
    timestamp: datetime
    category: AuditEventCategory
    user_id: str | None
    username: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    system_name: str  # "library" or "erp"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "system_name": self.system_name,
        }

    def to_json_line(self) -> str:
        return json.dumps(self.to_dict(), default=str, sort_keys=True)


# ---------------------------------------------------------------------------
# Action → category classifier
# ---------------------------------------------------------------------------

_MUTATION_KEYWORDS = {
    "create",
    "update",
    "delete",
    "post",
    "reverse",
    "close",
    "reopen",
    "sync",
    "login",
    "grant",
    "revoke",
    "remove",
    "run",
}

_SYSTEM_PREFIXES = (
    "system.",
    "scheduler.",
    "health.",
    "error.",
    "auth.failed",
)


def classify_action(action: str) -> AuditEventCategory:
    """Map an action string to a retention category."""
    action_lower = action.lower()

    # System events (prefixes)
    for prefix in _SYSTEM_PREFIXES:
        if action_lower.startswith(prefix):
            return AuditEventCategory.SYSTEM

    # Mutations: any segment that is a mutation keyword
    parts = action_lower.replace(".", "_").split("_")
    for part in parts:
        if part in _MUTATION_KEYWORDS:
            return AuditEventCategory.MUTATION

    # Read-access patterns
    read_keywords = ("view", "read", "list", "export", "report", "download")
    if any(kw in action_lower for kw in read_keywords):
        return AuditEventCategory.READ_ACCESS

    # Safety default: treat unknown as mutation (never deleted accidentally)
    return AuditEventCategory.MUTATION


# ---------------------------------------------------------------------------
# Triple audit writer
# ---------------------------------------------------------------------------


class TripleAuditWriter:
    """Manages writes to JSONL files and SQLite.

    PostgreSQL is handled separately by the existing ``write_audit_log()``
    function; this class handles the other two stores.
    """

    def __init__(self, base_path: str, system_name: str) -> None:
        self.base_path = Path(base_path)
        self.jsonl_dir = self.base_path / "jsonl"
        self.sqlite_path = self.base_path / "audit.db"
        self.system_name = system_name

        self.jsonl_dir.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()

    # ---- SQLite setup ----

    def _init_sqlite(self) -> None:
        conn = sqlite3.connect(str(self.sqlite_path))
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id          TEXT PRIMARY KEY,
                    timestamp   TEXT NOT NULL,
                    category    TEXT NOT NULL,
                    user_id     TEXT,
                    username    TEXT,
                    action      TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    details     TEXT,
                    ip_address  TEXT,
                    system_name TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ae_timestamp "
                "ON audit_events(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ae_category "
                "ON audit_events(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ae_action "
                "ON audit_events(action)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ae_cat_ts "
                "ON audit_events(category, timestamp)"
            )
            conn.commit()
        finally:
            conn.close()

    # ---- JSONL path helper ----

    def _get_jsonl_path(self, dt: datetime) -> Path:
        return self.jsonl_dir / f"{dt.strftime('%Y-%m-%d')}.jsonl"

    # ---- Sync write (runs in thread) ----

    def write_sync(self, event: AuditEvent) -> None:
        """Append to daily JSONL file and insert into SQLite."""
        # 1. JSONL
        jsonl_path = self._get_jsonl_path(event.timestamp)
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(event.to_json_line() + "\n")

        # 2. SQLite
        conn = sqlite3.connect(str(self.sqlite_path))
        try:
            conn.execute(
                """INSERT OR IGNORE INTO audit_events
                   (id, timestamp, category, user_id, username, action,
                    resource_type, resource_id, details, ip_address, system_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(event.id),
                    event.timestamp.isoformat(),
                    event.category.value,
                    event.user_id,
                    event.username,
                    event.action,
                    event.resource_type,
                    event.resource_id,
                    json.dumps(event.details) if event.details else None,
                    event.ip_address,
                    event.system_name,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # ---- Async / fire-and-forget ----

    async def write_async(self, event: AuditEvent) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.write_sync, event)

    def fire_and_forget(self, event: AuditEvent) -> None:
        """Schedule the write without awaiting.  Failures are logged only."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._safe_write(event))
        except RuntimeError:
            # No event loop -- sync fallback (e.g. during shutdown)
            try:
                self.write_sync(event)
            except Exception:
                logger.exception("Audit write failed (sync fallback)")

    async def _safe_write(self, event: AuditEvent) -> None:
        try:
            await self.write_async(event)
        except Exception:
            logger.exception("Audit triple-write failed for event %s", event.id)
