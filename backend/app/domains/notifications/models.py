"""
Modelo Notification.

Registro de alertas enviadas a usuarios.

Relaciones:
- Notification N:1 User
- Notification N:1 Insight
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, uuid_pk

if TYPE_CHECKING:
    from app.domains.auth.models import User
    from app.domains.insights.models import Insight

CHANNEL_VALUES = ("email_instant", "email_digest", "whatsapp")
NOTIF_STATUS_VALUES = ("pending", "sent", "failed")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insight_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("insights.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(sa.String, nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="pending",
        server_default="pending",
    )
    sent_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.CheckConstraint(f"channel IN {CHANNEL_VALUES}", name="ck_notifications_channel"),
        sa.CheckConstraint(f"status IN {NOTIF_STATUS_VALUES}", name="ck_notifications_status"),
    )

    # Relaciones
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    insight: Mapped["Insight"] = relationship("Insight", back_populates="notifications")
