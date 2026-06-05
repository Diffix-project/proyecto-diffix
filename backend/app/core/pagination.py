"""
Helper de paginación reutilizable.

Uso en servicios:
    from app.core.pagination import paginate, PaginatedResponse

    result = paginate(query, page=1, limit=20)
"""

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


class PaginatedResponse[T](BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    page: int
    limit: int
    total: int


def paginate(db: Session, stmt: Select, page: int, limit: int) -> tuple[list, int]:
    """
    Ejecuta una query paginada y retorna (items, total).

    page: 1-indexed.
    limit: cantidad por página.
    """
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(total_stmt).scalar_one()
    offset = (page - 1) * limit
    items = db.execute(stmt.offset(offset).limit(limit)).scalars().all()
    return list(items), total
