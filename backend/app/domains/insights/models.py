"""
Modelo Insight.

Un insight por Change (1:1). Generado por el Analyst Agent con LLM.

La columna `embedding` usa pgvector Vector(1536). Es nullable y solo se usa
en Postgres — en SQLite (tests) se omite vía create_all sin problema porque
la columna es nullable y SQLite ignora tipos desconocidos si se usa
NullType como fallback.

Relaciones:
- Insight 1:1 Change
- Insight 1:N Notification
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, uuid_pk

if TYPE_CHECKING:
    from app.domains.changes.models import Change
    from app.domains.notifications.models import Notification

try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

    _vector_type = Vector(1536)
except Exception:  # pragma: no cover
    # Fallback para entornos sin pgvector instalado (no debería ocurrir en prod)
    _vector_type = sa.Text()  # type: ignore[assignment]

URGENCY_VALUES = ("alta", "media", "baja")


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = uuid_pk()
    change_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("changes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1:1 con Change
    )
    what_changed: Mapped[str] = mapped_column(sa.Text, nullable=False)
    why_it_matters: Mapped[str] = mapped_column(sa.Text, nullable=False)
    what_to_do: Mapped[str] = mapped_column(sa.Text, nullable=False)
    urgency: Mapped[str] = mapped_column(sa.String, nullable=False)
    llm_model: Mapped[str] = mapped_column(sa.String, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    langfuse_trace_id: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    # Vector 1536 para búsqueda semántica (post-MVP). Nullable, solo Postgres.
    embedding: Mapped[list[float] | None] = mapped_column(
        _vector_type,
        nullable=True,
    )

    __table_args__ = (
        sa.Index("ix_insights_change_id", "change_id"),
        sa.Index("ix_insights_urgency", "urgency"),
        sa.Index("ix_insights_generated_at", "generated_at"),
        sa.CheckConstraint(f"urgency IN {URGENCY_VALUES}", name="ck_insights_urgency"),
    )

    # Relaciones
    change: Mapped["Change"] = relationship("Change", back_populates="insight")
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="insight"
    )
