"""Router del dominio competitors."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_db_user
from app.domains.auth.models import User
from app.domains.competitors import service
from app.domains.competitors.schemas import (
    CompetitorCreate,
    CompetitorOut,
    CompetitorUpdate,
    SourceIn,
    SourceOut,
)

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.get("", response_model=list[CompetitorOut])
def list_competitors(
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> list[CompetitorOut]:
    return [CompetitorOut.model_validate(c) for c in service.list_competitors(db, user)]


@router.post("", response_model=CompetitorOut, status_code=201)
def create_competitor(
    data: CompetitorCreate,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> CompetitorOut:
    competitor = service.create_competitor(db, user, data)
    return CompetitorOut.model_validate(competitor)


@router.get("/{competitor_id}", response_model=CompetitorOut)
def get_competitor(
    competitor_id: uuid.UUID,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> CompetitorOut:
    return CompetitorOut.model_validate(service.get_competitor(db, competitor_id, user))


@router.put("/{competitor_id}", response_model=CompetitorOut)
def update_competitor(
    competitor_id: uuid.UUID,
    data: CompetitorUpdate,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> CompetitorOut:
    return CompetitorOut.model_validate(service.update_competitor(db, competitor_id, user, data))


@router.delete("/{competitor_id}", status_code=204)
def delete_competitor(
    competitor_id: uuid.UUID,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> None:
    service.delete_competitor(db, competitor_id, user)


@router.get("/{competitor_id}/sources", response_model=list[SourceOut])
def list_sources(
    competitor_id: uuid.UUID,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> list[SourceOut]:
    return [SourceOut.model_validate(s) for s in service.list_sources(db, competitor_id, user)]


@router.post("/{competitor_id}/sources", response_model=SourceOut, status_code=201)
def add_source(
    competitor_id: uuid.UUID,
    data: SourceIn,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> SourceOut:
    return SourceOut.model_validate(service.add_source(db, competitor_id, user, data))


@router.delete("/{competitor_id}/sources/{source_id}", status_code=204)
def delete_source(
    competitor_id: uuid.UUID,
    source_id: uuid.UUID,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> None:
    service.delete_source(db, competitor_id, source_id, user)
