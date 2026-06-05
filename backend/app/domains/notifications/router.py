"""Router del dominio notifications y digests."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_db_user
from app.domains.auth.models import User
from app.domains.notifications import service
from app.domains.notifications.schemas import (
    DigestOut,
    NotificationSettingsOut,
    NotificationSettingsUpdate,
)

router = APIRouter(tags=["notifications"])


@router.get("/notifications/settings", response_model=NotificationSettingsOut)
def get_settings(
    user: User = Depends(get_current_db_user),
) -> NotificationSettingsOut:
    return NotificationSettingsOut.model_validate(user)


@router.put("/notifications/settings", response_model=NotificationSettingsOut)
def update_settings(
    data: NotificationSettingsUpdate,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> NotificationSettingsOut:
    updated = service.update_settings(db, user, data)
    return NotificationSettingsOut.model_validate(updated)


@router.get("/digests", response_model=list[DigestOut])
def list_digests(
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> list[DigestOut]:
    return [DigestOut.model_validate(d) for d in service.list_digests(db, user)]


@router.get("/digests/{digest_id}", response_model=DigestOut)
def get_digest(
    digest_id: uuid.UUID,
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> DigestOut:
    return DigestOut.model_validate(service.get_digest(db, digest_id, user))
