"""Organizational structure models: subsidiaries, departments, fiscal years/periods."""
from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.gl import JournalEntry


class Subsidiary(UUIDPrimaryKeyMixin, Base):
    """A legal entity / branch within the KAILASA network."""
    __tablename__ = "subsidiaries"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subsidiaries.id"),
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'USD'")
    )
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'UTC'")
    )
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    library_entity_code: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )

    # ------ relationships ------
    parent: Mapped[Subsidiary | None] = relationship(
        "Subsidiary",
        remote_side="Subsidiary.id",
        back_populates="children",
    )
    children: Mapped[list[Subsidiary]] = relationship(
        "Subsidiary",
        back_populates="parent",
    )
    departments: Mapped[list[Department]] = relationship(
        "Department",
        back_populates="subsidiary",
    )
    journal_entries: Mapped[list[JournalEntry]] = relationship(
        "JournalEntry",
        back_populates="subsidiary",
    )

    def __repr__(self) -> str:
        return f"<Subsidiary {self.code!r} {self.name!r}>"


class Department(UUIDPrimaryKeyMixin, Base):
    """Department within a subsidiary."""
    __tablename__ = "departments"

    subsidiary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subsidiaries.id"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )

    # ------ relationships ------
    subsidiary: Mapped[Subsidiary] = relationship(
        "Subsidiary",
        back_populates="departments",
    )

    def __repr__(self) -> str:
        return f"<Department {self.code!r} {self.name!r}>"


class FiscalYear(UUIDPrimaryKeyMixin, Base):
    """Fiscal year definition."""
    __tablename__ = "fiscal_years"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )

    # ------ relationships ------
    periods: Mapped[list[FiscalPeriod]] = relationship(
        "FiscalPeriod",
        back_populates="fiscal_year",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FiscalYear {self.name!r}>"


class FiscalPeriod(UUIDPrimaryKeyMixin, Base):
    """A single period within a fiscal year (e.g. a month or quarter)."""
    __tablename__ = "fiscal_periods"

    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fiscal_years.id"),
        nullable=False,
    )
    period_code: Mapped[str] = mapped_column(String(10), nullable=False)
    period_name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'open'"),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )

    # ------ relationships ------
    fiscal_year: Mapped[FiscalYear] = relationship(
        "FiscalYear",
        back_populates="periods",
    )

    def __repr__(self) -> str:
        return f"<FiscalPeriod {self.period_code!r} {self.period_name!r}>"
