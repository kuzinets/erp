"""General Ledger models: chart of accounts, journal entries, and journal lines."""
from __future__ import annotations

import datetime
import decimal
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.fund import Fund
    from app.models.org import Department, FiscalPeriod, Subsidiary
    from app.models.user import User


class Account(UUIDPrimaryKeyMixin, Base):
    """Chart of Accounts entry."""
    __tablename__ = "accounts"

    account_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    normal_balance: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
    )
    fund_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("funds.id"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )

    # ------ relationships ------
    parent: Mapped[Account | None] = relationship(
        "Account",
        remote_side="Account.id",
        back_populates="children",
    )
    children: Mapped[list[Account]] = relationship(
        "Account",
        back_populates="parent",
    )
    fund: Mapped[Fund | None] = relationship(
        "Fund",
        back_populates="accounts",
    )
    journal_lines: Mapped[list[JournalLine]] = relationship(
        "JournalLine",
        back_populates="account",
    )

    def __repr__(self) -> str:
        return f"<Account {self.account_number!r} {self.name!r}>"


class JournalEntry(UUIDPrimaryKeyMixin, Base):
    """A complete journal entry (header) containing one or more lines."""
    __tablename__ = "journal_entries"

    entry_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
        server_default=text("nextval('journal_entries_entry_number_seq')"),
    )
    subsidiary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subsidiaries.id"),
        nullable=False,
    )
    fiscal_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fiscal_periods.id"),
        nullable=False,
    )
    entry_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    memo: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'manual'"),
    )
    source_reference: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'draft'"),
    )
    posted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    posted_at: Mapped[datetime.datetime | None] = mapped_column()
    reversed_by_je_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id"),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
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
    subsidiary: Mapped[Subsidiary] = relationship(
        "Subsidiary",
        back_populates="journal_entries",
    )
    fiscal_period: Mapped[FiscalPeriod] = relationship(
        "FiscalPeriod",
        lazy="selectin",
    )
    lines: Mapped[list[JournalLine]] = relationship(
        "JournalLine",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    posted_by_user: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[posted_by],
        lazy="selectin",
    )
    created_by_user: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="selectin",
    )
    reversed_by_je: Mapped[JournalEntry | None] = relationship(
        "JournalEntry",
        remote_side="JournalEntry.id",
        foreign_keys=[reversed_by_je_id],
    )

    def __repr__(self) -> str:
        return f"<JournalEntry #{self.entry_number} status={self.status!r}>"


class JournalLine(UUIDPrimaryKeyMixin, Base):
    """Individual debit or credit line within a journal entry."""
    __tablename__ = "journal_lines"

    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
    )
    debit_amount: Mapped[decimal.Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default=text("0")
    )
    credit_amount: Mapped[decimal.Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default=text("0")
    )
    memo: Mapped[str | None] = mapped_column(Text)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id"),
    )
    fund_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("funds.id"),
    )
    cost_center: Mapped[str | None] = mapped_column(String(50))
    quantity: Mapped[decimal.Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default=text("'USD'")
    )
    exchange_rate: Mapped[decimal.Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, server_default=text("1.000000")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )

    # ------ relationships ------
    journal_entry: Mapped[JournalEntry] = relationship(
        "JournalEntry",
        back_populates="lines",
    )
    account: Mapped[Account] = relationship(
        "Account",
        back_populates="journal_lines",
        lazy="selectin",
    )
    department: Mapped[Department | None] = relationship(
        "Department",
        lazy="selectin",
    )
    fund: Mapped[Fund | None] = relationship(
        "Fund",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<JournalLine #{self.line_number} "
            f"debit={self.debit_amount} credit={self.credit_amount}>"
        )
