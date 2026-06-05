"""
Modelos Snapshot y Change.

Snapshot: estado histórico de una fuente.
Change: cambio detectado entre dos snapshots.

Relaciones:
- Snapshot N:1 Competitor
- Snapshot N:1 CompetitorSource
- Change N:1 Competitor
- Change N:1 CompetitorSource
- Change 0:1 Snapshot (before)
- Change 1:1 Snapshot (after)
- Change 1:1 Insight
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, uuid_pk

if TYPE_CHECKING:
    from app.domains.competitors.models import Competitor
    from app.domains.insights.models import Insight
    from app.domains.sources.models import CompetitorSource

# source_type valid values (duplicado aquí para que Change no dependa de sources.models en runtime)
SOURCE_TYPE_VALUES = ("website", "mercadolibre", "jobs", "pdf")
SECTION_VALUES = ("pricing", "home", "features", "jobs", "pdf", "general")
CHANGE_STATUS_VALUES = ("pending", "analyzing", "done", "failed", "ignored")

# JSONB en Postgres, JSON en SQLite
_jsonb_type = JSONB().with_variant(PG_JSON(), "sqlite")


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[uuid.UUID] = uuid_pk()
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("competitor_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    content_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)  # SHA256 hex
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    raw_url: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.Index("ix_snapshots_competitor_source", "competitor_id", "source_id"),
        sa.Index("ix_snapshots_captured_at", "captured_at"),
        sa.CheckConstraint(f"source_type IN {SOURCE_TYPE_VALUES}", name="ck_snapshots_source_type"),
    )

    # Relaciones
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="snapshots")
    source: Mapped["CompetitorSource"] = relationship(
        "CompetitorSource", back_populates="snapshots"
    )


class Change(Base):
    __tablename__ = "changes"

    id: Mapped[uuid.UUID] = uuid_pk()
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("competitor_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    section: Mapped[str] = mapped_column(sa.String, nullable=False)
    diff_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    diff_raw: Mapped[dict | None] = mapped_column(_jsonb_type, nullable=True)
    snapshot_before_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    snapshot_after_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    detected_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="pending",
        server_default="pending",
    )

    __table_args__ = (
        sa.Index("ix_changes_competitor_id", "competitor_id"),
        sa.Index("ix_changes_status", "status"),
        sa.Index("ix_changes_detected_at", "detected_at"),
        sa.CheckConstraint(f"source_type IN {SOURCE_TYPE_VALUES}", name="ck_changes_source_type"),
        sa.CheckConstraint(f"section IN {SECTION_VALUES}", name="ck_changes_section"),
        sa.CheckConstraint(f"status IN {CHANGE_STATUS_VALUES}", name="ck_changes_status"),
    )

    # Relaciones
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="changes")
    source: Mapped["CompetitorSource"] = relationship("CompetitorSource", back_populates="changes")
    snapshot_before: Mapped["Snapshot | None"] = relationship(
        "Snapshot",
        foreign_keys=[snapshot_before_id],
    )
    snapshot_after: Mapped["Snapshot"] = relationship(
        "Snapshot",
        foreign_keys=[snapshot_after_id],
    )
    insight: Mapped["Insight | None"] = relationship(
        "Insight", back_populates="change", uselist=False
    )
