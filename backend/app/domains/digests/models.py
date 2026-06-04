"""
Modelo Digest.

Resúmenes semanales enviados a usuarios.

La columna `insight_ids` es ARRAY(UUID) en Postgres y JSON en SQLite
(para tests), usando with_variant.

Relaciones:
- Digest N:1 User
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, uuid_pk

if TYPE_CHECKING:
    from app.domains.auth.models import User

DIGEST_STATUS_VALUES = ("pending", "sent", "failed")

# ARRAY(UUID) en Postgres, JSON en SQLite (almacena lista de strings UUID)
_insight_ids_type = ARRAY(UUID(as_uuid=False)).with_variant(PG_JSON(), "sqlite")


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    # Lista de UUIDs de insights incluidos en el digest
    insight_ids: Mapped[list | None] = mapped_column(_insight_ids_type, nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="pending",
        server_default="pending",
    )
    sent_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.CheckConstraint(f"status IN {DIGEST_STATUS_VALUES}", name="ck_digests_status"),
    )

    # Relaciones
    user: Mapped["User"] = relationship("User", back_populates="digests")
