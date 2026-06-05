"""
Piezas base para todos los modelos SQLAlchemy del proyecto.

Convenciones:
- Importar `Base` desde `app.core.base` para heredar en cada modelo.
- Usar `TimestampMixin` para agregar created_at / updated_at automáticos.
- Usar `uuid_pk()` para declarar el campo `id` UUID con default uuid4.

Ejemplo de modelo:
    from app.core.base import Base, TimestampMixin, uuid_pk

    class MyModel(TimestampMixin, Base):
        __tablename__ = "my_models"
        id = uuid_pk()
        name: Mapped[str]
"""

import uuid
from typing import Annotated

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedColumn,
    mapped_column,
)

# ─── Base declarativa ────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


# ─── Tipo anotado reutilizable para PKs UUID ─────────────────────────────────

# Uso: id: Mapped[UUIDType] = mapped_column(primary_key=True)
# O directamente con la función helper uuid_pk() definida abajo.
UUIDType = Annotated[uuid.UUID, MappedColumn(UUID(as_uuid=True))]


def uuid_pk() -> MappedColumn:
    """Columna UUID PK con default uuid4. Usar como atributo de clase en modelos."""
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# ─── Mixin de timestamps ─────────────────────────────────────────────────────


class TimestampMixin:
    """Agrega created_at y updated_at a cualquier modelo que lo herede."""

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
