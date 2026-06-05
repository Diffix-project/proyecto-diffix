"""
Modelo CompetitorSource.

Una fila por cada fuente activa de un competidor.

Relaciones:
- CompetitorSource N:1 Competitor
- CompetitorSource 1:N Snapshot
- CompetitorSource 1:N Change
"""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, uuid_pk

if TYPE_CHECKING:
    from app.domains.changes.models import Change, Snapshot
    from app.domains.competitors.models import Competitor

# Tipos de fuente válidos
SOURCE_TYPE_VALUES = ("website", "mercadolibre", "jobs", "pdf")

# JSONB en Postgres, JSON en SQLite (para tests)
_config_type = JSONB().with_variant(PG_JSON(), "sqlite")


class CompetitorSource(Base):
    __tablename__ = "competitor_sources"

    id: Mapped[uuid.UUID] = uuid_pk()
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    config: Mapped[dict | None] = mapped_column(_config_type, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.true()
    )
    last_checked_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"source_type IN {SOURCE_TYPE_VALUES}", name="ck_competitor_sources_source_type"
        ),
    )

    # Relaciones
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="sources")
    snapshots: Mapped[list["Snapshot"]] = relationship("Snapshot", back_populates="source")
    changes: Mapped[list["Change"]] = relationship("Change", back_populates="source")
