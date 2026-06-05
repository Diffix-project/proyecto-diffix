"""Schemas Pydantic para el dominio competitors."""

import uuid
from datetime import datetime  # noqa: TCH003
from typing import Literal

from pydantic import BaseModel, ConfigDict

# Tipos de fuente válidos — debe coincidir con SOURCE_TYPE_VALUES y el CheckConstraint
# de app.domains.sources.models.CompetitorSource. Validar acá evita que un valor inválido
# llegue a la DB y dispare un IntegrityError (HTTP 500) en lugar de un 422 limpio.
SourceTypeLiteral = Literal["website", "mercadolibre", "jobs", "pdf"]

# ─── Sources (embebidos en competitor) ───────────────────────────────────────


class SourceIn(BaseModel):
    source_type: SourceTypeLiteral
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
