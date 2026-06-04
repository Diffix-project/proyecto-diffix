"""
Modelos de autenticación: User y Company.

Relaciones:
- User 1:1 Company (user_id UNIQUE en companies)
- User 1:N Competitor (via Company)
- User 1:N Notification
- User 1:N Digest
"""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.domains.competitors.models import Competitor
    from app.domains.digests.models import Digest
    from app.domains.notifications.models import Notification

# Valores válidos para plan — String + CheckConstraint (portable a SQLite)
PLAN_VALUES = ("free", "starter", "growth", "business")
INDUSTRY_VALUES = ("food", "tech", "construction", "other")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    clerk_id: Mapped[str] = mapped_column(sa.String, unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(sa.String, nullable=False)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)

    # Plan de suscripción
    plan: Mapped[str] = mapped_column(
        sa.String,
        nullable=False,
        default="free",
        server_default="free",
    )
    plan_expires_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Preferencias de notificación
    notif_email_instant: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.true()
    )
    notif_email_digest: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.true()
    )
    notif_whatsapp: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False, server_default=sa.false()
    )
    whatsapp_number: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    __table_args__ = (sa.CheckConstraint(f"plan IN {PLAN_VALUES}", name="ck_users_plan"),)

    # Relaciones
    company: Mapped["Company | None"] = relationship(
        "Company", back_populates="user", uselist=False
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
    digests: Mapped[list["Digest"]] = relationship("Digest", back_populates="user")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1:1 con User
    )
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    industry: Mapped[str] = mapped_column(sa.String, nullable=False)
    country: Mapped[str] = mapped_column(
        sa.String, nullable=False, default="AR", server_default="AR"
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.CheckConstraint(f"industry IN {INDUSTRY_VALUES}", name="ck_companies_industry"),
    )

    # Relaciones
    user: Mapped["User"] = relationship("User", back_populates="company")
    competitors: Mapped[list["Competitor"]] = relationship("Competitor", back_populates="company")
