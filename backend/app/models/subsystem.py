"""Subsystem integration models for connecting external systems (Library, Temple, etc.)."""
from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.gl import Account
    from app.models.org import Subsidiary


class SubsystemConfig(UUIDPrimaryKeyMixin, Base):
    """Configuration for an external subsystem that feeds data into the ERP."""
    __tablename__ = "subsystem_configs"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    system_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_username: Mapped[str | None] = mapped_column(String(100))
    api_password_hash: Mapped[str | None] = mapped_column(String(200))
    subsidiary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subsidiaries.id"),
        nullable=False,
    )
    sync_frequency_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("60")
    )
    last_sync_at: Mapped[datetime.datetime | None] = mapped_column()
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
        lazy="selectin",
    )
    account_mappings: Mapped[list[SubsystemAccountMapping]] = relationship(
        "SubsystemAccountMapping",
        back_populates="subsystem_config",
        cascade="all, delete-orphan",
    )
    sync_logs: Mapped[list[SyncLog]] = relationship(
        "SyncLog",
        back_populates="subsystem_config",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SubsystemConfig {self.name!r} type={self.system_type!r}>"


class SubsystemAccountMapping(UUIDPrimaryKeyMixin, Base):
    """Maps a source account code from a subsystem to a GL account in the ERP."""
    __tablename__ = "subsystem_account_mappings"

    subsystem_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subsystem_configs.id"),
        nullable=False,
    )
    source_account_code: Mapped[str] = mapped_column(String(50), nullable=False)
    target_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
    )
    source_posting_type: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    # ------ relationships ------
    subsystem_config: Mapped[SubsystemConfig] = relationship(
        "SubsystemConfig",
        back_populates="account_mappings",
    )
    target_account: Mapped[Account] = relationship(
        "Account",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<SubsystemAccountMapping {self.source_account_code!r} -> "
            f"account={self.target_account_id!r}>"
        )


class SyncLog(UUIDPrimaryKeyMixin, Base):
    """Log entry for a subsystem synchronization run."""
    __tablename__ = "sync_logs"

    subsystem_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subsystem_configs.id"),
        nullable=False,
    )
    started_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'running'"),
    )
    fiscal_period_synced: Mapped[str | None] = mapped_column(String(10))
    postings_imported: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    journal_entries_created: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSONB)

    # ------ relationships ------
    subsystem_config: Mapped[SubsystemConfig] = relationship(
        "SubsystemConfig",
        back_populates="sync_logs",
    )

    def __repr__(self) -> str:
        return (
            f"<SyncLog config={self.subsystem_config_id!r} "
            f"status={self.status!r}>"
        )
