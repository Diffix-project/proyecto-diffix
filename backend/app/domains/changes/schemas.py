"""Schemas Pydantic para el dominio changes."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InsightSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    what_changed: str
    why_it_matters: str
    what_to_do: str
    urgency: str
    generated_at: datetime


class ChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competitor_id: uuid.UUID
    source_id: uuid.UUID
    source_type: str
    section: str
    diff_text: str
    detected_at: datetime
    status: str
    insight: InsightSummary | None = None
