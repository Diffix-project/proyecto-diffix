"""Schemas Pydantic para el dominio notifications."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notif_email_instant: bool
    notif_email_digest: bool
    notif_whatsapp: bool
    whatsapp_number: str | None


class NotificationSettingsUpdate(BaseModel):
    email_instant: bool | None = None
    email_digest: bool | None = None
    whatsapp: bool | None = None
    whatsapp_number: str | None = None


class DigestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    insight_ids: list | None
    status: str
    sent_at: datetime | None
    created_at: datetime
