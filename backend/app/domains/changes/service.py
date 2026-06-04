"""Lógica de dominio para changes."""

import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.pagination import PaginatedResponse, paginate
from app.domains.auth.models import Company, User
from app.domains.changes.models import Change
from app.domains.changes.schemas import ChangeOut
from app.domains.competitors.models import Competitor
from app.domains.insights.models import Insight


def _company(user: User) -> Company:
    if user.company is None:
        raise HTTPException(status_code=400, detail="El usuario no tiene empresa configurada.")
    return user.company


def list_changes(
    db: Session,
    user: User,
    page: int,
    limit: int,
    competitor_id: uuid.UUID | None,
    source_type: str | None,
    urgency: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> PaginatedResponse[ChangeOut]:
    company = _company(user)

    stmt = (
        select(Change)
        .join(Competitor, Change.competitor_id == Competitor.id)
        .where(
            Competitor.company_id == company.id,
            Change.status != "ignored",
        )
        .order_by(Change.detected_at.desc())
    )

    if competitor_id is not None:
        stmt = stmt.where(Change.competitor_id == competitor_id)
    if source_type is not None:
        stmt = stmt.where(Change.source_type == source_type)
    if from_date is not None:
        stmt = stmt.where(Change.detected_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Change.detected_at <= to_date)
    if urgency is not None:
        stmt = stmt.join(Insight, Change.id == Insight.change_id).where(Insight.urgency == urgency)

    items, total = paginate(db, stmt, page, limit)
    return PaginatedResponse(
        items=[ChangeOut.model_validate(c) for c in items],
        page=page,
        limit=limit,
        total=total,
    )


def get_change(db: Session, change_id: uuid.UUID, user: User) -> Change:
    company = _company(user)
    change = (
        db.query(Change)
        .join(Competitor, Change.competitor_id == Competitor.id)
        .filter(
            Change.id == change_id,
            Competitor.company_id == company.id,
        )
        .first()
    )
    if change is None:
        raise HTTPException(status_code=404, detail="Cambio no encontrado")
    return change


def ignore_change(db: Session, change_id: uuid.UUID, user: User) -> Change:
    change = get_change(db, change_id, user)
    change.status = "ignored"
    db.commit()
    db.refresh(change)
    return change
