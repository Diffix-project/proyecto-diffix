"""
Modelo Competitor.

Relaciones:
- Competitor N:1 Company
- Competitor 1:N CompetitorSource
- Competitor 1:N Snapshot
- Competitor 1:N Change
"""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.domains.auth.models import Company
    from app.domains.changes.models import Change, Snapshot
    from app.domains.sources.models import CompetitorSource


class Competitor(TimestampMixin, Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    website_url: Mapped[str] = mapped_column(sa.String, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.true()
    )

    # Relaciones
    company: Mapped["Company"] = relationship("Company", back_populates="competitors")
    sources: Mapped[list["CompetitorSource"]] = relationship(
        "CompetitorSource", back_populates="competitor"
    )
    snapshots: Mapped[list["Snapshot"]] = relationship("Snapshot", back_populates="competitor")
    changes: Mapped[list["Change"]] = relationship("Change", back_populates="competitor")
