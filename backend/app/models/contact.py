"""Contact model for donors, vendors, volunteers, and members."""
from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.org import Subsidiary


class Contact(UUIDPrimaryKeyMixin, Base):
    """A contact record (donor, vendor, volunteer, member, or other)."""
    __tablename__ = "contacts"

    contact_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(30))
    address_line_1: Mapped[str | None] = mapped_column(String(200))
    address_line_2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    subsidiary_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subsidiaries.id"),
    )
    notes: Mapped[str | None] = mapped_column(Text)
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
        return f"<Contact {self.name!r} type={self.contact_type!r}>"
