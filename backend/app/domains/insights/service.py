"""Lógica de dominio para insights."""

import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.pagination import PaginatedResponse, paginate
from app.domains.auth.models import Company, User
from app.domains.changes.models import Change
from app.domains.competitors.models import Competitor
from app.domains.insights.models import Insight
from app.domains.insights.schemas import InsightOut


def _company(user: User) -> Company:
    if user.company is None:
        raise HTTPException(status_code=400, detail="El usuario no tiene empresa configurada.")
    return user.company


def list_insights(
    db: Session,
    user: User,
    page: int,
    limit: int,
    urgency: str | None,
    competitor_id: uuid.UUID | None,
    from_date: datetime | None,
) -> PaginatedResponse[InsightOut]:
    company = _company(user)

    stmt = (
        select(Insight)
        .join(Change, Insight.change_id == Change.id)
        .join(Competitor, Change.competitor_id == Competitor.id)
        .where(Competitor.company_id == company.id)
        .order_by(Insight.generated_at.desc())
    )

    if urgency is not None:
        stmt = stmt.where(Insight.urgency == urgency)
    if competitor_id is not None:
        stmt = stmt.where(Change.competitor_id == competitor_id)
    if from_date is not None:
        stmt = stmt.where(Insight.generated_at >= from_date)

    items, total = paginate(db, stmt, page, limit)
    return PaginatedResponse(
        items=[InsightOut.model_validate(i) for i in items],
        page=page,
        limit=limit,
        total=total,
    )


def get_insight(db: Session, insight_id: uuid.UUID, user: User) -> Insight:
    company = _company(user)
    insight = (
        db.query(Insight)
        .join(Change, Insight.change_id == Change.id)
        .join(Competitor, Change.competitor_id == Competitor.id)
        .filter(
            Insight.id == insight_id,
            Competitor.company_id == company.id,
        )
        .first()
    )
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight no encontrado")
    return insight
