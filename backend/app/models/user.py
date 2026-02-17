"""User model for ERP authentication and authorization."""
from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.org import Subsidiary


class User(UUIDPrimaryKeyMixin, Base):
    """An ERP system user with role-based access."""
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    subsidiary_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subsidiaries.id"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )

    # ------ relationships ------
    subsidiary: Mapped[Subsidiary | None] = relationship(
        "Subsidiary",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User {self.username!r} role={self.role!r}>"
