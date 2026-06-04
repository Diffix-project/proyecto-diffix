"""Router del dominio insights."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_db_user
from app.core.pagination import PaginatedResponse
from app.domains.auth.models import User
from app.domains.insights import service
from app.domains.insights.schemas import InsightOut

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=PaginatedResponse[InsightOut])
def list_insights(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    urgency: str | None = Query(None),
    competitor_id: uuid.UUID | None = Query(None),
    from_date: datetime | None = Query(None),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InsightOut]:
    return service.list_insights(db, user, page, limit, urgency, competitor_id, from_date)


@router.get("/{insight_id}", response_model=InsightOut)
def get_insight(
    insight_id: uuid.UUID,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> InsightOut:
    return InsightOut.model_validate(service.get_insight(db, insight_id, user))
