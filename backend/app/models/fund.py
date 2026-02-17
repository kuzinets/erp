"""Fund accounting model for restricted/unrestricted fund tracking."""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.gl import Account


class Fund(UUIDPrimaryKeyMixin, Base):
    """A fund for nonprofit fund accounting (unrestricted, temporarily/permanently restricted)."""
    __tablename__ = "funds"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    fund_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
    )

    # ------ relationships ------
    accounts: Mapped[list[Account]] = relationship(
        "Account",
        back_populates="fund",
    )

    def __repr__(self) -> str:
        return f"<Fund {self.code!r} {self.name!r} type={self.fund_type!r}>"
