"""Schemas Pydantic para el dominio competitors."""

import uuid
from datetime import datetime  # noqa: TCH003

from pydantic import BaseModel, ConfigDict

# ─── Sources (embebidos en competitor) ───────────────────────────────────────


class SourceIn(BaseModel):
    source_type: str
    source_url: str | None = None
    config: dict | None = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competitor_id: uuid.UUID
    source_type: str
    source_url: str | None
    config: dict | None
    is_active: bool
    last_checked_at: datetime | None
    created_at: datetime


# ─── Competitor ───────────────────────────────────────────────────────────────


class CompetitorCreate(BaseModel):
    name: str
    website_url: str
    sources: list[SourceIn] = []


class CompetitorUpdate(BaseModel):
    name: str | None = None
    website_url: str | None = None


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    website_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
