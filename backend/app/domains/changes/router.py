"""Router del dominio changes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_db_user
from app.core.pagination import PaginatedResponse
from app.domains.auth.models import User
from app.domains.changes import service
from app.domains.changes.schemas import ChangeOut

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("", response_model=PaginatedResponse[ChangeOut])
def list_changes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    competitor_id: uuid.UUID | None = Query(None),
    source_type: str | None = Query(None),
    urgency: str | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ChangeOut]:
    return service.list_changes(
        db, user, page, limit, competitor_id, source_type, urgency, from_date, to_date
    )


@router.get("/{change_id}", response_model=ChangeOut)
def get_change(
    change_id: uuid.UUID,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> ChangeOut:
    return ChangeOut.model_validate(service.get_change(db, change_id, user))


@router.put("/{change_id}/ignore", response_model=ChangeOut)
def ignore_change(
    change_id: uuid.UUID,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> ChangeOut:
    return ChangeOut.model_validate(service.ignore_change(db, change_id, user))
