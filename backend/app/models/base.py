"""Base model utilities for the KAILASA ERP system.

Provides a UUID primary-key mixin so every model automatically gets
a ``id`` column of type ``UUID`` with a server-side default.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Mixin that adds a UUID primary key column named ``id``."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
