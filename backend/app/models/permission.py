"""SQLAlchemy models for RBAC: permission overrides and audit logging."""
from __future__ import annotations

import datetime
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin


class UserPermissionOverride(UUIDPrimaryKeyMixin, Base):
    """Per-user permission grant/revoke override.

    Used by the AI-advanced mode to grant temporary permissions or
    revoke specific permissions from a user beyond their role defaults.
    """
    __tablename__ = "user_permission_overrides"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission: Mapped[str] = mapped_column(String(100), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column()
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=text("NOW()")
    )

    def __repr__(self) -> str:
        action = "grant" if self.granted else "revoke"
        return f"<Override {action} {self.permission!r} for user {self.user_id}>"


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Immutable audit trail of all system mutations."""
    __tablename__ = "audit_log"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    username: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(200))
    details: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    event_category: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'mutation'")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=text("NOW()")
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action!r} by {self.username!r}>"
