"""Lógica de dominio para notifications y digests."""

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domains.auth.models import User
from app.domains.digests.models import Digest
from app.domains.notifications.schemas import NotificationSettingsUpdate


def get_settings(user: User) -> User:
    return user


def update_settings(db: Session, user: User, data: NotificationSettingsUpdate) -> User:
    if data.email_instant is not None:
        user.notif_email_instant = data.email_instant
    if data.email_digest is not None:
        user.notif_email_digest = data.email_digest
    if data.whatsapp is not None:
        user.notif_whatsapp = data.whatsapp
    if data.whatsapp_number is not None:
        user.whatsapp_number = data.whatsapp_number
    db.commit()
    db.refresh(user)
    return user


def list_digests(db: Session, user: User) -> list[Digest]:
    return (
        db.query(Digest).filter(Digest.user_id == user.id).order_by(Digest.created_at.desc()).all()
    )


def get_digest(db: Session, digest_id: uuid.UUID, user: User) -> Digest:
    digest = db.query(Digest).filter(Digest.id == digest_id, Digest.user_id == user.id).first()
    if digest is None:
        raise HTTPException(status_code=404, detail="Digest no encontrado")
    return digest
